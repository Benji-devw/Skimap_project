from django.contrib import admin
from .models import Station, Piste, SnowMeasure

# Register your models here.
@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "geometry")

@admin.register(Piste)
class PisteAdmin(admin.ModelAdmin):
    list_display = ("id", "nom", "station_id", "geometry")

@admin.register(SnowMeasure)
class SnowMeasureAdmin(admin.ModelAdmin):
    list_display = ("id", "date_heure", "temperature_c", "precipitations_mm", "hauteur_neige_totale_cm", "hauteur_neige_naturelle_cm", "hauteur_neige_artificielle_cm", "production_neige_artificielle_m3", "station_id")
