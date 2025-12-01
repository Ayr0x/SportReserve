from django.contrib import admin
from .models import Cancha, Reserva

# Esto hace que se vean bonito en el panel
class CanchaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_hora', 'superficie')

class ReservaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cancha', 'fecha', 'pagado')
    list_filter = ('pagado', 'fecha')

admin.site.register(Cancha, CanchaAdmin)
admin.site.register(Reserva, ReservaAdmin)