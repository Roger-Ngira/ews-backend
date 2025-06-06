from rest_framework import serializers
from .models import AfricanCity, PrecipitationRecords, Watershed
import json

class AfricanCitySerializer(serializers.ModelSerializer):
    # Expose a GeoJSON‐style coordinate pair [lon, lat]
    location = serializers.SerializerMethodField()

    class Meta:
        model = AfricanCity
        fields = [
            "id",
            "city",
            "country",
            "location",
            "population",
            "warning_level",
        ]

    def get_location(self, obj):
        if obj.location:
            # obj.location.x is longitude, obj.location.y is latitude
            return [obj.location.x, obj.location.y]
        return None


class PrecipitationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecipitationRecords
        fields = ["date", "precipitation"]


class WatershedSerializer(serializers.ModelSerializer):
    geom = serializers.SerializerMethodField()

    class Meta:
        model = Watershed
        fields = [
            "id",
            "name",
            "warning_level",
            "geom",
        ]

    def get_geom(self, obj):
        """
        Return a GeoJSON dict for the MultiPolygon stored in obj.geom.
        `obj.geom.geojson` is a string of the GeoJSON geometry—e.g. '{"type":"MultiPolygon", ... }'
        We parse it with `json.loads(...)` so that the API returns a JSON object,
        not a string.
        """
        if not obj.geom:
            return None
        # `geom.geojson` is a string, so we load it into a Python dict and return.
        return json.loads(obj.geom.geojson)