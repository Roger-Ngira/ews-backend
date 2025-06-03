from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import AfricanCity, PrecipitationRecords
from .serializers import PrecipitationRecordSerializer, AfricanCitySerializer

class AfricanCityListAPIView(APIView):
    def get(self, request):
        cities = AfricanCity.objects.all()
        output = []

        for city in cities:
            # all precipitation records for this city, sorted by date (oldest → newest)
            records = (
                PrecipitationRecords.objects
                .filter(city=city)
                .order_by("date")
            )

            # Build a simple list of floats (skipping any nulls)
            daily_vals = [rec.precipitation for rec in records if rec.precipitation is not None]

            # Compute the sliding 4-day window sums (including shorter windows at the beginning)
            max_window_sum = 0.0
            n = len(daily_vals)

            # We can do this in O(n) by maintaining a small deque / sliding-sum:
            if n > 0:
                #summing the first “up to 4” days
                # running sum of the last up to 4 days and update max_window_sum as we go.
                window_sum = 0.0
                from collections import deque
                last_four = deque()  # will hold up to 4 most recent values

                for val in daily_vals:
                    # Push the new day's precipitation
                    last_four.append(val)
                    window_sum += val

                    # If we now have more than 4 values, pop the oldest
                    if len(last_four) > 4:
                        oldest = last_four.popleft()
                        window_sum -= oldest

                    # Check if this window (size = len(last_four), up to 4) is the largest so far
                    if window_sum > max_window_sum:
                        max_window_sum = window_sum

            # Decide the warning_level based on that maximum 4-day sum
            if max_window_sum > 40:
                warning_level = "red"
            elif max_window_sum > 10:
                warning_level = "orange"
            else:
                warning_level = "green"

            # Build the minimal for frontend
            output.append({
                "id": city.id,
                "city": city.city,
                "country": city.country,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "warning_level": warning_level,
            })

        return Response(output)

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
    
    