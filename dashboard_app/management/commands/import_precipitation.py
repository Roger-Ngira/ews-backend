import asyncio
import aiohttp
import csv
import io
from datetime import date, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from dashboard_app.models import AfricanCity, PrecipitationRecords

OWM_URL = "https://pro.openweathermap.org/data/2.5/forecast/daily"
MAX_CONCURRENT = 50  # keep ~50 in flight to respect 3 000/minute
RATE_LIMIT_PAUSE = 1 / 50  # simple per‐request spacing

async def fetch_one(session, city):
    lat, lon = city.latitude, city.longitude
    params = {
        "lat": lat,
        "lon": lon,
        "cnt": 7,
        "units": "metric",
        "appid": settings.OWM_API_KEY,
    }
    try:
        async with session.get(OWM_URL, params=params, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
            result = []
            for day in data.get("list", []):
                dt_date = date.fromtimestamp(day["dt"])
                rain_mm = float(day.get("rain", 0.0))
                result.append((city.id, dt_date, rain_mm))
            return result
    except Exception as e:
        print(f"❌ {city.city}: {e}")
        return None

async def fetch_all(cities):
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for city in cities:
            await sem.acquire()
            task = asyncio.create_task(
                _wrapper(sem, fetch_one, session, city)
            )
            tasks.append(task)
            # simple spacing so we don’t “burst” > 50/sec
            await asyncio.sleep(RATE_LIMIT_PAUSE)

        all_results = await asyncio.gather(*tasks)
        # Flatten out None’s and nested lists
        flat = []
        for res in all_results:
            if res:
                flat.extend(res)
        return flat

async def _wrapper(sem, coro, session, city):
    try:
        return await coro(session, city)
    finally:
        sem.release()

def bulk_upsert(records):
    """
    records: list of (city_id, date, precip)
    Uses a temp table + COPY + INSERT...ON CONFLICT.
    """
    if not records:
        return

    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TEMP TABLE tmp_precip (
                city_id INTEGER,
                date DATE,
                precipitation REAL
            ) ON COMMIT DROP;
        """)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for city_id, dt_date, precip in records:
            writer.writerow([city_id, dt_date.isoformat(), precip])
        buffer.seek(0)

        cursor.copy_expert(
            "COPY tmp_precip (city_id, date, precipitation) FROM STDIN WITH CSV",
            buffer
        )

        cursor.execute("""
            INSERT INTO dashboard_app_precipitationrecords (city_id, date, precipitation)
            SELECT city_id, date, precipitation FROM tmp_precip
            ON CONFLICT (city_id, date)
            DO UPDATE SET precipitation = EXCLUDED.precipitation;
        """)

class Command(BaseCommand):
    help = "Fetch 7-day forecasts for all AfricanCity entries, upsert into PrecipitationRecords."

    def handle(self, *args, **options):
        cities = list(AfricanCity.objects.all())
        total = len(cities)
        self.stdout.write(f"🔄 Fetching 7-day forecasts for {total} cities…")

        # Phase 1: Network calls (no DB transaction here)
        all_tuples = asyncio.run(fetch_all(cities))
        self.stdout.write(f"✅ Fetched {len(all_tuples)} day-records. Upserting…")

        # Phase 2: Upsert in one short transaction
        with transaction.atomic():
            bulk_upsert(all_tuples)

        self.stdout.write("🎉 Upsert complete.")
