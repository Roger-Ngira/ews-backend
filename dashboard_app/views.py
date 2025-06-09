from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import AfricanCity, PrecipitationRecords,
from .serializers import AfricanCitySerializer, PrecipitationRecordSerializer, WatershedSerializer

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

        records = PrecipitationRecords.objects.filter(city=city).order_by("date")
        serializer = PrecipitationRecordSerializer(records, many=True)
        return Response(serializer.data)


class WatershedListAPIView(APIView):
    def get(self, request):
        """
        Returns a list of all BV_… watersheds, each with:
        {
          "id": ..,
          "name": "..",
          "warning_level": "..",
          "geom": { …GeoJSON MultiPolygon… }
        }
        """
        qs = Watershed.objects.all()
        serializer = WatershedSerializer(qs, many=True)
        return Response(serializer.data)