from django.urls import path
from .views import AfricanCityListAPIView, PrecipitationForecastAPIView, WatershedListAPIView

urlpatterns = [
    path('cities/', AfricanCityListAPIView.as_view(), name='city-list'),
    path(
        "cities/<int:city_id>/forecast/",
        PrecipitationForecastAPIView.as_view(),
        name="city-forecast",
    ),
    path("watersheds/", WatershedListAPIView.as_view(), name="watershed-list"),
]