from django.urls import path
from . import views

urlpatterns = [
    path("stations", views.stations),
    path("pistes/<int:station_id>", views.pistes_par_station),
    path("stations/proches", views.stations_proches),
]