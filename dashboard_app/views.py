from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AfricanCity
from .serializers import AfricanCitySerializer

class AfricanCityListAPIView(APIView):
    def get(self, request):
        cities = AfricanCity.objects.all()
        serializer = AfricanCitySerializer(cities, many=True)
        return Response(serializer.data)
