from django.urls import path
from .views import AfricanCityListAPIView, PrecipitationForecastAPIView

urlpatterns = [
    path('cities/', AfricanCityListAPIView.as_view(), name='city-list'),
    path(
        "cities/<int:city_id>/forecast/",
        PrecipitationForecastAPIView.as_view(),
        name="city-forecast",
    ),
]