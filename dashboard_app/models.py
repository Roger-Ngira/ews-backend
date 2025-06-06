# dashboard_app/models.py

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.db.models import Avg, Q

class Watershed(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Human-readable name for this watershed (filename without .shp)"
    )
    # Use MultiPolygonField so that both single Polygons and MultiPolygons will work
    geom = gis_models.MultiPolygonField(
        srid=4326,
        null=True,    # temporarily allow NULL until you re-import every row
        blank=True,   # you can remove both null=True/blank=True after import
        help_text="Watershed boundary (MULTIPOLYGON) in EPSG:4326"
    )
    warning_level = models.CharField(
        max_length=6,
        choices=[("green", "Green"), ("orange", "Orange"), ("red", "Red")],
        default="green",
        help_text="Precomputed 4-day precipitation warning for the watershed"
    )

    def __str__(self):
        return self.name

    def average_precipitation_on(self, date):
        """
        Return the average precipitation (Float) over all cities in this watershed
        for a given `date`. If no records exist, returns None.
        """
        result = (
            PrecipitationRecords.objects
                .filter(city__watershed=self, date=date)
                .aggregate(avg_precip=Avg("precipitation"))
        )
        return result["avg_precip"]

    @classmethod
    def annotate_avg_precip_for_date(cls, date):
        """
        Return a queryset of Watershed objects, each annotated with 'avg_precip'
        over all its cities' precipitation_records for the given date.
        Usage:
            Watershed.annotate_avg_precip_for_date(today).filter(avg_precip__gt=0)
        """
        return cls.objects.annotate(
            avg_precip=Avg(
                "cities__precipitation_records__precipitation",
                filter=Q(cities__precipitation_records__date=date)
            )
        )


class AfricanCity(models.Model):
    city = models.CharField(max_length=100)
    country_code = models.CharField(max_length=10, default="N/A")
    country = models.CharField(max_length=50)

    # Allow existing rows to remain NULL; you'll populate them in the import step
    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Exact lat/lon (EPSG:4326) of this city"
    )

    population = models.BigIntegerField(null=True, blank=True)

    watershed = models.ForeignKey(
        Watershed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cities",
        help_text="Which watershed this city is in (if known)"
    )

    warning_level = models.CharField(
        max_length=6,
        choices=[("green", "Green"), ("orange", "Orange"), ("red", "Red")],
        default="green",
        help_text="Precomputed 4-day precipitation warning"
    )

    def __str__(self):
        return f"{self.city}, {self.country}"


class PrecipitationRecords(models.Model):
    city = models.ForeignKey(
        AfricanCity,
        on_delete=models.CASCADE,
        related_name='precipitation_records'
    )
    date = models.DateField(help_text='Date of the precipitation record')
    precipitation = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('city', 'date')  # Avoid one row per city+date
        ordering = ['date']

    def __str__(self):
        return f"{self.city.city} on {self.date}: {self.precipitation} mm"


class TestGeo(models.Model):
    name = models.CharField(max_length=50)
    location = gis_models.PointField(srid=4326)

    def __str__(self):
        return self.name
