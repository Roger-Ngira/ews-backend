from django.db import models

# Create your models here.
class AfricanCity(models.Model):
    city = models.CharField(max_length=100)
    country_code = models.CharField(max_length=10, default="N/A")
    country = models.CharField(max_length=50)
    latitude = models.FloatField()
    longitude = models.FloatField()
    population = models.BigIntegerField(null=True, blank=True, help_text="Latest population (from OWM)")

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