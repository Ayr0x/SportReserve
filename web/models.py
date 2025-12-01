from django.db import models
from django.contrib.auth.models import User
import datetime

class Cancha(models.Model):
    OPCIONES_SUPERFICIE = [
        ('Sintetico', 'Pasto Sintético'),
        ('Cemento', 'Cemento/Baby'),
        ('Natural', 'Pasto Natural'),
    ]
    
    # blank=True, null=True permite que existan canchas sin dueño (admin)
    dueno = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='canchas_propias', verbose_name="Dueño de la Cancha")

    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio_hora = models.IntegerField()
    superficie = models.CharField(max_length=20, choices=OPCIONES_SUPERFICIE, default='Sintetico')
    # Ojo: Necesitas instalar Pillow para usar ImageField (pip install Pillow)
    imagen = models.ImageField(upload_to='canchas/', null=True, blank=True)

    # --- NUEVOS CAMPOS DE HORARIO ---
    hora_apertura = models.TimeField(default=datetime.time(9, 0), verbose_name="Hora de Apertura")
    hora_cierre = models.TimeField(default=datetime.time(22, 0), verbose_name="Hora de Cierre")
    abre_feriados = models.BooleanField(default=True, verbose_name="¿Abre feriados?")

    def __str__(self):
        return f"{self.nombre} - ${self.precio_hora}"

class Reserva(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    codigo_reserva = models.CharField(max_length=100, blank=True, null=True)
    pagado = models.BooleanField(default=False) # Para integración con Flow
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha} ({self.hora_inicio}) - Pagado: {self.pagado}"