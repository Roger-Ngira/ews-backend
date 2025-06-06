import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import Polygon, MultiPolygon

from dashboard_app.models import Watershed

class Command(BaseCommand):
    help = (
        "Import only BV_*.shp (basin polygons) from data/BVS.\n"
        "Each BV_XXXX.shp becomes a Watershed(name='BV_XXXX').\n"
        "Reprojects each feature into EPSG:4326 and wraps single Polygons as MultiPolygons."
    )

    def handle(self, *args, **options):
        # １) Where the shapefiles live
        SHAPEFILES_DIR = os.path.join(settings.BASE_DIR, "data", "BVS")
        if not os.path.isdir(SHAPEFILES_DIR):
            self.stderr.write(f"Directory not found: {SHAPEFILES_DIR}")
            return

        # ２) Only gather filenames that end in .shp *and* start with "BV_"
        shapefiles = []
        for fname in os.listdir(SHAPEFILES_DIR):
            if not fname.lower().endswith(".shp"):
                continue
            base = os.path.splitext(fname)[0]   # e.g. "BV_AGADEZ1"
            if base.upper().startswith("BV_"):
                shapefiles.append(os.path.join(SHAPEFILES_DIR, fname))

        if not shapefiles:
            self.stderr.write(f"No BV_*.shp files found in {SHAPEFILES_DIR}")
            return

        self.stdout.write(f"Found {len(shapefiles)} BV_*.shp file(s) in {SHAPEFILES_DIR}.\n")

        # ３) Loop through each BV_*.shp
        for shp_path in sorted(shapefiles):
            basename = os.path.splitext(os.path.basename(shp_path))[0]

            # If a row with this name already exists, skip it
            if Watershed.objects.filter(name=basename).exists():
                self.stdout.write(f"  • Skipping '{basename}' (already imported)\n")
                continue

            self.stdout.write(f"Processing '{basename}.shp'…")
            try:
                ds = DataSource(shp_path)
                layer = ds[0]  # shapefile typically has one layer

                count = 0
                for feature in layer:
                    geom = feature.geom
                    geom.transform(4326)          # reproject to EPSG:4326
                    geos_geom = geom.geos        # GEOS Geometry

                    # If it's just a Polygon, wrap it as a MultiPolygon
                    if isinstance(geos_geom, Polygon):
                        geos_geom = MultiPolygon(geos_geom)

                    # Create the Watershed row
                    Watershed.objects.create(name=basename, geom=geos_geom)
                    count += 1

                self.stdout.write(self.style.SUCCESS(
                    f"  → Imported {count} feature(s) from '{basename}.shp' "
                    f"as Watershed(name='{basename}')\n"
                ))

            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"  ✖ Error processing '{basename}.shp': {e}\n"
                ))

        self.stdout.write(self.style.SUCCESS("All BV_*.shp files processed."))