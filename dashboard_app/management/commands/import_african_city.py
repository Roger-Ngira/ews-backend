import json
import os
from django.core.management.base import BaseCommand
from dashboard_app.models import AfricanCity

COUNTRY_NAMES = {
    "DZ": "Algeria", "AO": "Angola", "BJ": "Benin", "BW": "Botswana", "BF": "Burkina Faso",
    "BI": "Burundi", "CM": "Cameroon", "CV": "Cape Verde", "CF": "Central African Republic",
    "TD": "Chad", "KM": "Comoros", "CG": "Congo (Brazzaville)", "CD": "Congo (Kinshasa)",
    "DJ": "Djibouti", "EG": "Egypt", "GQ": "Equatorial Guinea", "ER": "Eritrea", "SZ": "Eswatini",
    "ET": "Ethiopia", "GA": "Gabon", "GM": "Gambia", "GH": "Ghana", "GN": "Guinea",
    "GW": "Guinea-Bissau", "CI": "Ivory Coast", "KE": "Kenya", "LS": "Lesotho", "LR": "Liberia",
    "LY": "Libya", "MG": "Madagascar", "MW": "Malawi", "ML": "Mali", "MR": "Mauritania",
    "MU": "Mauritius", "MA": "Morocco", "MZ": "Mozambique", "NA": "Namibia", "NE": "Niger",
    "NG": "Nigeria", "RW": "Rwanda", "ST": "São Tomé and Príncipe", "SN": "Senegal",
    "SC": "Seychelles", "SL": "Sierra Leone", "SO": "Somalia", "ZA": "South Africa",
    "SS": "South Sudan", "SD": "Sudan", "TZ": "Tanzania", "TG": "Togo", "TN": "Tunisia",
    "UG": "Uganda", "EH": "Western Sahara", "ZM": "Zambia", "ZW": "Zimbabwe"
}

class Command(BaseCommand):
    help = "Import African cities from OpenWeatherMap JSON"

    def handle(self, *args, **options):
        african_codes = set(COUNTRY_NAMES.keys())
        json_path = os.path.join("data", "city.list.json")

        if not os.path.exists(json_path):
            self.stderr.write(f"File not found: {json_path}")
            return

        with open(json_path, encoding="utf-8") as f:
            city_data = json.load(f)

        count = 0
        for city in city_data:
            code = city["country"]
            if code in african_codes:
                AfricanCity.objects.get_or_create(
                    city=city["name"],
                    country_code=code,
                    country=COUNTRY_NAMES.get(code, ""),
                    latitude=city["coord"]["lat"],
                    longitude=city["coord"]["lon"]
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} African cities imported."))
