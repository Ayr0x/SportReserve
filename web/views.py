from django.shortcuts import render, redirect, get_object_or_404
from .models import Cancha, Reserva

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail
import json
import requests
import hmac
import hashlib
import uuid
import os # <--- IMPORTANTE: Necesario para leer variables de entorno
from datetime import datetime, date, time
from django.contrib import messages

# ==========================================
# CONFIGURACIÓN DE FLOW (SEGURA)
# ==========================================
# Ahora leemos las claves desde el archivo oculto .env
FLOW_API_KEY = os.getenv('FLOW_API_KEY')
FLOW_SECRET_KEY = os.getenv('FLOW_SECRET_KEY')
FLOW_URL = 'https://sandbox.flow.cl/api' 

# LISTA FERIADOS
FERIADOS_CHILE = [
    '2024-12-08', '2024-12-25',
    '2025-01-01', '2025-04-18', '2025-04-19', '2025-05-01', '2025-05-21',
    '2025-06-29', '2025-06-30', '2025-07-16', '2025-08-15', '2025-09-18',
    '2025-09-19', '2025-10-31', '2025-11-01', '2025-12-08', '2025-12-25',
    '2026-01-01', '2026-04-03', '2026-04-04', '2026-05-01', '2026-05-21',
    '2026-06-15', '2026-06-29', '2026-07-16', '2026-08-17', '2026-09-18',
    '2026-09-19', '2026-11-01', '2026-11-02', '2026-12-08', '2026-12-25'
]

# ==========================================
# FUNCIÓN CORREO
# ==========================================
def enviar_correo_reserva(usuario, reserva, tipo="confirmacion"):
    if tipo == "confirmacion":
        asunto = f"Reserva Confirmada - {reserva.cancha.nombre}"
        mensaje = f"""
        Hola {usuario.first_name},

        Tu reserva ha sido confirmada exitosamente.
        ------------------------------------------
        Cancha: {reserva.cancha.nombre}
        Dirección: {reserva.cancha.direccion}
        Fecha: {reserva.fecha}
        Hora: {reserva.hora_inicio}
        Código: {reserva.codigo_reserva}
        ------------------------------------------
        ¡Te esperamos en la cancha!
        """
    elif tipo == "cancelacion":
        asunto = f"Reserva Cancelada - {reserva.cancha.nombre}"
        mensaje = f"""
        Hola {usuario.first_name},

        Te informamos que tu reserva ha sido cancelada.
        ------------------------------------------
        Cancha: {reserva.cancha.nombre}
        Fecha: {reserva.fecha}
        Hora: {reserva.hora_inicio}
        
        Estado: { "Solicitud de reembolso en proceso" if reserva.pagado else "Cancelación directa" }
        ------------------------------------------
        """
    else:
        return

    try:
        send_mail(
            asunto,
            mensaje,
            settings.EMAIL_HOST_USER, 
            [usuario.email],          
            fail_silently=True        
        )
    except Exception as e:
        print(f"Error enviando correo: {e}")

# ==========================================
# VISTAS
# ==========================================

def index(request):
    canchas = Cancha.objects.all()
    es_dueno = False
    if request.user.is_authenticated:
        es_dueno = Cancha.objects.filter(dueno=request.user).exists()
    
    return render(request, 'index.html', {
        'canchas': canchas,
        'es_dueno': es_dueno
    })

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        mensaje = data.get('message', '').lower()
        user = request.user
        
        respuesta = "No entendi tu consulta. Puedes preguntar por disponibilidad, tu ultima reserva o canchas en tu comuna."
        todas_canchas = Cancha.objects.all()
        ahora = datetime.now()
        hoy = date.today()

        if any(p in mensaje for p in ['mi reserva', 'ultima reserva', 'que reserve', 'tengo hora']):
            if not user.is_authenticated:
                respuesta = "Para ver tus reservas necesitas iniciar sesion primero."
            else:
                ultima = Reserva.objects.filter(usuario=user).order_by('-fecha', '-hora_inicio').first()
                if ultima:
                    estado = "Pagada" if ultima.pagado else "Pendiente"
                    respuesta = f"Tu ultima reserva registrada es en {ultima.cancha.nombre} para el {ultima.fecha} a las {ultima.hora_inicio}. Estado: {estado}."
                else:
                    respuesta = "No encontre reservas asociadas a tu cuenta."

        elif any(p in mensaje for p in ['comuna', 'region', 'donde hay', 'en que parte', 'tienes en']):
            canchas_encontradas = []
            for c in todas_canchas:
                direccion_limpia = c.direccion.lower()
                if any(word in mensaje for word in direccion_limpia.split()): 
                    palabras_clave = [p for p in mensaje.split() if len(p) > 4]
                    for p in palabras_clave:
                        if p in direccion_limpia:
                            canchas_encontradas.append(c.nombre)
                            break
            
            if not canchas_encontradas:
                 for c in todas_canchas:
                     if "santiago" in mensaje and "santiago" in c.direccion.lower():
                         canchas_encontradas.append(c.nombre)
                     elif "norte" in mensaje and "norte" in c.direccion.lower():
                         canchas_encontradas.append(c.nombre)

            if canchas_encontradas:
                lista = ", ".join(set(canchas_encontradas))
                respuesta = f"Si, en esa zona tenemos las siguientes canchas: {lista}."
            else:
                respuesta = "No encontre canchas en esa ubicacion especifica."

        elif any(p in mensaje for p in ['disponible', 'hora', 'cupo', 'jugar']):
            cancha_detectada = None
            for c in todas_canchas:
                if c.nombre.lower() in mensaje:
                    cancha_detectada = c
                    break
            
            if cancha_detectada:
                reservadas = Reserva.objects.filter(
                    cancha=cancha_detectada, 
                    fecha=hoy, 
                    pagado=True
                ).values_list('hora_inicio', flat=True)

                horas_libres = []
                hora_iter = cancha_detectada.hora_apertura.hour
                
                while hora_iter < cancha_detectada.hora_cierre.hour:
                    tiempo_obj = time(hora_iter, 0)
                    if tiempo_obj not in reservadas:
                        if tiempo_obj > ahora.time(): 
                            horas_libres.append(tiempo_obj.strftime("%H:%M"))
                    hora_iter += 1
                
                if horas_libres:
                    muestras = ", ".join(horas_libres[:3])
                    respuesta = f"Para hoy en {cancha_detectada.nombre} quedan estas horas: {muestras}... y mas. Ve al calendario para reservar."
                else:
                    respuesta = f"Lo siento, {cancha_detectada.nombre} no tiene horas disponibles por hoy."
            else:
                respuesta = "Dime el nombre de la cancha para ver disponibilidad."

        elif any(p in mensaje for p in ['direccion', 'calle', 'ubicacion', 'llegar']):
            cancha_detectada = None
            for c in todas_canchas:
                if c.nombre.lower() in mensaje:
                    cancha_detectada = c
                    break
            
            if cancha_detectada:
                respuesta = f"La direccion exacta de {cancha_detectada.nombre} es: {cancha_detectada.direccion}."
            else:
                respuesta = "Tenemos varias ubicaciones. Preguntame por una cancha especifica."

        elif 'precio' in mensaje:
            respuesta = "Los precios varian segun la cancha. Puedes ver el detalle en la lista de arriba."
        
        elif 'hola' in mensaje:
            respuesta = "Hola. Soy el asistente inteligente. Preguntame por reservas, disponibilidad o ubicaciones."

        elif any(p in mensaje for p in ['chau', 'adios', 'hasta luego', 'nos vemos', 'gracias']):
            respuesta = "Hasta pronto! Espero verte jugando pronto en nuestras canchas."

        return JsonResponse({'reply': respuesta})
    
    return JsonResponse({'error': 'Metodo no permitido'}, status=405)

@login_required
def reserva_detalle(request, cancha_id):
    cancha = get_object_or_404(Cancha, id=cancha_id)
    fecha_str = request.GET.get('fecha')
    
    bloques_manana = []
    bloques_tarde = []
    mensaje_alerta = None
    es_feriado_cerrado = False

    if fecha_str:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        if fecha_str in FERIADOS_CHILE and not cancha.abre_feriados:
            es_feriado_cerrado = True
            mensaje_alerta = "Este recinto permanece cerrado los días feriados."
        else:
            reservas_existentes = Reserva.objects.filter(
                cancha=cancha, 
                fecha=fecha_str, 
                pagado=True
            ).values_list('hora_inicio', flat=True)

            ahora = datetime.now()
            es_hoy = (fecha_obj == ahora.date())
            hora_actual = ahora.time()

            hora_iter = cancha.hora_apertura.hour
            hora_fin = cancha.hora_cierre.hour
            
            while hora_iter < hora_fin:
                tiempo_bloque = time(hora_iter, 0)
                hora_str = tiempo_bloque.strftime("%H:%M")
                estado = 'disponible'
                
                if tiempo_bloque in reservas_existentes:
                    estado = 'ocupado'
                elif es_hoy and tiempo_bloque <= hora_actual:
                    estado = 'pasado'

                bloque_data = {'hora': hora_str, 'estado': estado}

                if hora_iter < 12:
                    bloques_manana.append(bloque_data)
                else:
                    bloques_tarde.append(bloque_data)
                
                hora_iter += 1

    return render(request, 'reserva_detalle.html', {
        'cancha': cancha,
        'fecha_seleccionada': fecha_str,
        'bloques_manana': bloques_manana,
        'bloques_tarde': bloques_tarde,
        'mensaje_alerta': mensaje_alerta,
        'es_feriado_cerrado': es_feriado_cerrado
    })

@login_required
def procesar_pago(request):
    if request.method == 'POST':
        cancha_id = request.POST.get('cancha_id')
        fecha = request.POST.get('fecha')
        horas_seleccionadas = request.POST.getlist('horas[]') 
        
        cancha = get_object_or_404(Cancha, id=cancha_id)
        
        if not horas_seleccionadas:
            return redirect('reserva_detalle', cancha_id=cancha_id)

        codigo_unico = str(uuid.uuid4())
        total_a_pagar = int(cancha.precio_hora) * len(horas_seleccionadas)
        
        for hora in horas_seleccionadas:
            Reserva.objects.create(
                usuario=request.user,
                cancha=cancha,
                fecha=fecha,
                hora_inicio=hora,
                codigo_reserva=codigo_unico,
                pagado=False
            )

        base_url = request.build_absolute_uri('/')[:-1]

        params = {
            "amount": total_a_pagar,
            "apiKey": FLOW_API_KEY,
            "commerceOrder": codigo_unico,
            "currency": "CLP",
            "email": request.user.email,
            "media": "9",
            "subject": f"Reserva {cancha.nombre}",
            "urlConfirmation": f"{base_url}/pago/retorno/",
            "urlReturn": f"{base_url}/pago/retorno/",
        }

        cadena = "".join([f"{k}{v}" for k, v in sorted(params.items())])
        signature = hmac.new(FLOW_SECRET_KEY.encode(), cadena.encode(), hashlib.sha256).hexdigest()
        params["s"] = signature

        try:
            response = requests.post(f"{FLOW_URL}/payment/create", data=params)
            data = response.json()
            if "token" in data:
                return redirect(f"{data['url']}?token={data['token']}")
        except Exception as e:
            print(f"Error Flow: {e}")
            
    return redirect('index')

@csrf_exempt
def retorno_pago(request):
    token = request.POST.get('token') if request.method == 'POST' else request.GET.get('token')
    if not token: return redirect('index')

    params = {"apiKey": FLOW_API_KEY, "token": token}
    cadena = "".join([f"{k}{v}" for k, v in sorted(params.items())])
    signature = hmac.new(FLOW_SECRET_KEY.encode(), cadena.encode(), hashlib.sha256).hexdigest()
    params["s"] = signature

    try:
        response = requests.get(f"{FLOW_URL}/payment/getStatus", params=params)
        data = response.json()
        
        if data.get('status') == 2: # Pagado
            codigo_unico = data.get('commerceOrder')
            reservas_afectadas = Reserva.objects.filter(codigo_reserva=codigo_unico)
            reservas_afectadas.update(pagado=True)
            
            if reservas_afectadas.exists():
                enviar_correo_reserva(reservas_afectadas.first().usuario, reservas_afectadas.first(), "confirmacion")
            
            return render(request, 'exito.html', {
                'reserva': reservas_afectadas.first(), 
                'cantidad': reservas_afectadas.count()
            })
            
    except Exception as e:
        print(f"Error Retorno: {e}")

    return redirect('index')

@login_required
def mis_reservas(request):
    reservas = Reserva.objects.filter(usuario=request.user).order_by('-fecha', '-hora_inicio')
    mes_filtro = request.GET.get('mes')
    
    if mes_filtro and mes_filtro != 'todos':
        reservas = reservas.filter(fecha__month=mes_filtro)

    return render(request, 'mis_reservas.html', {
        'reservas': reservas,
        'mes_actual': mes_filtro
    })

@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)

    if request.method == 'POST':
        datos_reserva = reserva 
        es_pagada = reserva.pagado
        nombre_cancha = reserva.cancha.nombre
        fecha = reserva.fecha

        enviar_correo_reserva(request.user, datos_reserva, "cancelacion")

        reserva.delete()

        if es_pagada:
            messages.success(request, f"Reserva cancelada. Correo de respaldo enviado.")
        else:
            messages.info(request, "Reserva eliminada.")
            
    return redirect('mis_reservas')

def contacto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        telefono = request.POST.get('telefono')
        email_cliente = request.POST.get('email')
        mensaje_cliente = request.POST.get('mensaje')

        asunto = f"SportReserve Nuevo Contacto Web: {nombre}"
        cuerpo_mensaje = f"""
        Has recibido un nuevo mensaje desde la web SportReserve.
        
        ------------------------------------------
        DATOS DEL INTERESADO:
        ------------------------------------------
        Nombre: {nombre}
        Teléfono: {telefono}
        Email: {email_cliente}
        
        MENSAJE:
        {mensaje_cliente}
        ------------------------------------------
        """

        try:
            send_mail(
                asunto,
                cuerpo_mensaje,
                settings.EMAIL_HOST_USER, 
                [settings.EMAIL_HOST_USER], 
                fail_silently=False
            )
            messages.success(request, "¡Mensaje enviado! Nos pondremos en contacto contigo pronto.")
        except Exception as e:
            messages.error(request, "Hubo un error al enviar el mensaje. Intenta nuevamente.")
            print(f"Error Contacto: {e}")

    return redirect('/#contacto')

@login_required
def dashboard_dueno(request):
    mis_canchas = Cancha.objects.filter(dueno=request.user)
    
    if not mis_canchas.exists():
        messages.error(request, "No tienes canchas asignadas para administrar.")
        return redirect('index')

    fecha_str = request.GET.get('fecha', str(date.today()))
    try:
        fecha_filtro = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        fecha_filtro = date.today()

    reservas = Reserva.objects.filter(
        cancha__in=mis_canchas,
        fecha=fecha_filtro
    ).order_by('hora_inicio')

    ganancia_total = sum(r.cancha.precio_hora for r in reservas if r.pagado)

    return render(request, 'dashboard_dueno.html', {
        'reservas': reservas,
        'fecha_actual': fecha_str,
        'canchas': mis_canchas,
        'ganancia_total': ganancia_total
    })