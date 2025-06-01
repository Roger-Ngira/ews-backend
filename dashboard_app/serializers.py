from rest_framework import serializers
from .models import AfricanCity

class AfricanCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AfricanCity
        fields = '__all__'
