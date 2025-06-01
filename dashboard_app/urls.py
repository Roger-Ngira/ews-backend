from django.urls import path
from .views import AfricanCityListAPIView

urlpatterns = [
    path('cities/', AfricanCityListAPIView.as_view(), name='city-list'),
]