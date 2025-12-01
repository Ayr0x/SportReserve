from django.contrib import admin
from django.urls import path, include # 'include' es necesario para traer las rutas de Google
from django.conf import settings
from django.conf.urls.static import static
from web import views

urlpatterns = [
    # Panel de administración
    path('admin/', admin.site.urls),

    # Tu página principal
    path('', views.inicio, name='index'),

    # --- RUTAS MÁGICAS DE GOOGLE LOGIN (ALLAUTH) ---
    # Esto genera automáticamente:
    # /accounts/google/login/ -> Iniciar con Google
    # /accounts/logout/ -> Cerrar sesión
    # /accounts/profile/ -> Perfil (aunque redirigimos al index)
    path('accounts/', include('allauth.urls')),
    
    # Ruta para el cerebro del Chatbot (API)
    path('api/chat/', views.chat_api, name='chat_api'),

    # --- RUTAS DE PAGO (NUEVAS - FASE 5) ---
    # A. Pantalla de Calendario: Muestra la cancha y permite seleccionar horas
    path('reserva/detalle/<int:cancha_id>/', views.reserva_detalle, name='reserva_detalle'),
    
    # B. Procesador de Pago: Recibe las horas seleccionadas, suma el total y manda a Flow
    # (Nota: Ya no recibe el ID por URL, porque viene oculto en el formulario)
    path('pago/procesar/', views.procesar_pago, name='procesar_pago'),
    
    # C. Retorno desde Flow
    path('pago/retorno/', views.retorno_pago, name='retorno_pago'),

    # --- GESTIÓN DE MIS RESERVAS (FASE 6) ---
    
    # D. Ver historial (con filtros)
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),

    # E. Cancelar reserva (Libera el cupo y simula reembolso)
    path('reserva/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),

    # --- RUTA DE CONTACTO (NUEVA) ---
    path('contacto/', views.contacto, name='contacto'),

    # --- PANEL DE DUEÑO (NUEVA RUTA) ---
    path('dashboard/', views.dashboard_dueno, name='dashboard_dueno'),
]

# Configuración de imágenes en modo desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)