"""
URL configuration for skimap_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from stations.views import (
    PisteViewSet,
    SnowMeasureViewSet,
    StationViewSet,
    lidar_cancel,
    lidar_status,
    lidar_upload,
    lidar_upload_delete,
    lidar_uploads_list,
    snow_at_point,
    snow_coverage_geojson,
    snow_realtime,
    snow_refresh,
)


def health(_request):
    return JsonResponse({"status": "ok"})


router = DefaultRouter()
router.register(r"stations", StationViewSet, basename="station")
router.register(r"pistes", PisteViewSet, basename="piste")
router.register(r"snow_measures", SnowMeasureViewSet, basename="snow_measure")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/", include(router.urls)),
    path("api/snow-coverage/", snow_coverage_geojson, name="snow-coverage"),
    path("api/snow-at-point/", snow_at_point, name="snow-at-point"),
    path("api/snow-realtime/", snow_realtime, name="snow-realtime"),
    path("api/lidar/upload/", lidar_upload, name="lidar-upload"),
    path("api/lidar/uploads/", lidar_uploads_list, name="lidar-uploads-list"),
    path(
        "api/lidar/uploads/<int:upload_id>/",
        lidar_upload_delete,
        name="lidar-upload-delete",
    ),
    path("api/lidar/status/", lidar_status, name="lidar-status"),
    path("api/lidar/cancel/", lidar_cancel, name="lidar-cancel"),
    path("api/snow/refresh/", snow_refresh, name="snow-refresh"),
]
