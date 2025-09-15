from django.contrib import admin
from .models import Station, Piste

# Register your models here.
@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "geometry")

@admin.register(Piste)
class PisteAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "station_id", "geometry")