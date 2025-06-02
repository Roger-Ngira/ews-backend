from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import AfricanCity, PrecipitationRecords
from .serializers import PrecipitationRecordSerializer, AfricanCitySerializer

class AfricanCityListAPIView(APIView):
    def get(self, request):
        cities = AfricanCity.objects.all()
        serializer = AfricanCitySerializer(cities, many=True)
        return Response(serializer.data)

class PrecipitationForecastAPIView(APIView):
    """
    Returns the next 7 days of precipitation for a given city ID.
    URL: /api/cities/<int:city_id>/forecast/
    """
    def get(self, request, city_id):
        try:
            city = AfricanCity.objects.get(pk=city_id)
        except AfricanCity.DoesNotExist:
            return Response({"detail": "City not found."}, status=status.HTTP_404_NOT_FOUND)

        # Assume you always have exactly 7 future records per city 
        # (from your import_precipitation job). If not, you can filter by date ≥ today.
        records = PrecipitationRecords.objects.filter(city=city).order_by("date")
        serializer = PrecipitationRecordSerializer(records, many=True)
        return Response(serializer.data)