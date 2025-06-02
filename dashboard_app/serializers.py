from rest_framework import serializers
from .models import AfricanCity, PrecipitationRecords

class AfricanCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AfricanCity
        fields = '__all__'

class PrecipitationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecipitationRecords
        fields = ["date", "precipitation"]