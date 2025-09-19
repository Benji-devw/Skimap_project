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
    list_display = ("id", "date_time", "temperature_c", "precipitation_mm", "total_snow_height_cm", "natural_snow_height_cm", "artificial_snow_height_cm", "artificial_snow_production_m3", "station_id")
