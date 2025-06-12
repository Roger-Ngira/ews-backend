import asyncio
import aiohttp
import csv
import io
from datetime import date, datetime, timedelta
from collections import deque

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from dashboard_app.models import AfricanCity, PrecipitationRecords, Watershed

OWM_URL = "https://pro.openweathermap.org/data/2.5/forecast/daily"
MAX_CONCURRENT = 50
RATE_LIMIT_PAUSE = 1 / 50

async def fetch_one(session, city):
    if not city.location:
        # no Point stored? skip this city
        return None

    lon = city.location.x
    lat = city.location.y

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
            city_info = data.get("city", {})
            population = city_info.get("population", None)

            tuples = []
            for day in data.get("list", []):
                dt_date = date.fromtimestamp(day["dt"])
                rain_mm = float(day.get("rain", 0.0) or 0.0)
                tuples.append((city.id, dt_date, rain_mm))

            return (city.id, population, tuples)
    except Exception as e:
        print(f"[>>] {city.city}: {e}")
        return None

async def fetch_all(cities):
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for city in cities:
            await sem.acquire()
            task = asyncio.create_task(_wrapper(sem, fetch_one, session, city))
            tasks.append(task)
            await asyncio.sleep(RATE_LIMIT_PAUSE)
        results = await asyncio.gather(*tasks)
    all_records = []
    pop_map = {}
    for res in results:
        if not res:
            continue
        city_id, population, tuples = res
        all_records.extend(tuples)
        if population is not None:
            pop_map[city_id] = population
    return all_records, pop_map

async def _wrapper(sem, coro, session, city):
    try:
        return await coro(session, city)
    finally:
        sem.release()

def bulk_upsert(records):
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
    help = "Fetch forecasts, update population, recompute warnings (cities + watersheds), prune old/future, and report completion time."

    def handle(self, *args, **options):
        cities = list(AfricanCity.objects.all())
        start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.stdout.write(f"[>>] Starting fetch for {len(cities)} cities at {start}")

        all_records, pop_map = asyncio.run(fetch_all(cities))

        with transaction.atomic():
            # 1) bulk upsert precipitation values
            bulk_upsert(all_records)

            # 2) prune old / future precipitation records
            today = date.today()
            lower_cutoff = today - timedelta(days=3)
            upper_cutoff = today + timedelta(days=7)
            PrecipitationRecords.objects.filter(date__lt=lower_cutoff).delete()
            PrecipitationRecords.objects.filter(date__gt=upper_cutoff).delete()

            # 3) update each city's population (if provided by OWM)
            for city_id, population in pop_map.items():
                AfricanCity.objects.filter(id=city_id).update(population=population)

            # 4) recompute each city's own warning_level (4‐day rolling sum)
            for city in AfricanCity.objects.all():
                recs = PrecipitationRecords.objects.filter(city=city).order_by("date")
                vals = [r.precipitation for r in recs if r.precipitation is not None]

                max_sum = 0.0
                window_sum = 0.0
                dq = deque()

                for v in vals:
                    dq.append(v)
                    window_sum += v
                    if len(dq) > 4:
                        window_sum -= dq.popleft()
                    if window_sum > max_sum:
                        max_sum = window_sum

                new_level = "green"
                if max_sum > 40:
                    new_level = "red"
                elif max_sum > 10:
                    new_level = "orange"

                if city.warning_level != new_level:
                    AfricanCity.objects.filter(id=city.id).update(warning_level=new_level)

            for ws in Watershed.objects.all():
                # collect warning_level strings for all cities in this watershed
                city_levels = list(ws.cities.values_list("warning_level", flat=True))
                if "red" in city_levels:
                    ws_new = "red"
                elif "orange" in city_levels:
                    ws_new = "orange"
                else:
                    ws_new = "green"

                if ws.warning_level != ws_new:
                    # save the new level
                    ws.warning_level = ws_new
                    ws.save(update_fields=["warning_level"])
            # ───────────────────────────────────────────────────────────────────

        end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.stdout.write(f"Update complete at {end}")
