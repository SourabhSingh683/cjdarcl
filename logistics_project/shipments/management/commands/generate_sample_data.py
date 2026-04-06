"""
Management command to generate a sample Excel file for testing the upload pipeline.
Usage: python manage.py generate_sample_data [--rows 200] [--output sample_shipments.xlsx]
"""

import random
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a sample Excel file with fake shipment data for testing"

    def add_arguments(self, parser):
        parser.add_argument("--rows", type=int, default=200, help="Number of rows")
        parser.add_argument("--output", type=str, default="sample_shipments.xlsx", help="Output file name")

    def handle(self, *args, **options):
        rows = options["rows"]
        output = options["output"]

        cities = [
            "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
            "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
            "Chandigarh", "Indore", "Nagpur", "Surat", "Bhopal",
        ]
        vehicle_types = ["truck", "trailer", "container", "van"]

        data = []
        base_date = date(2025, 1, 1)

        for i in range(1, rows + 1):
            origin = random.choice(cities)
            destination = random.choice([c for c in cities if c != origin])

            dispatch = base_date + timedelta(days=random.randint(0, 365))
            transit_days = random.randint(1, 10)
            expected_delivery = dispatch + timedelta(days=transit_days)

            # 70% on time, 30% delayed by 1-5 days
            if random.random() < 0.70:
                actual_delivery = expected_delivery - timedelta(days=random.randint(0, 2))
            else:
                actual_delivery = expected_delivery + timedelta(days=random.randint(1, 5))

            data.append({
                "shipment_id": f"CN{1000 + i}",
                "origin": origin,
                "destination": destination,
                "dispatch_date": dispatch.isoformat(),
                "delivery_date": actual_delivery.isoformat(),
                "expected_delivery_date": expected_delivery.isoformat(),
                "revenue": round(random.uniform(10000, 95000), 2),
                "vehicle_type": random.choice(vehicle_types),
                "vehicle_no": f"JH05AB{random.randint(1000, 9999)}",
                "consignor_name": "TATA STEEL LIMITED",
                "consignee_name": "RUNGTA MINES LIMITED",
                "transporter_name": "RAMESHWAR SINGH & SONS",
            })

        df = pd.DataFrame(data)
        df.to_excel(output, index=False, engine="openpyxl")
        self.stdout.write(self.style.SUCCESS(f"Generated {rows} rows → {output}"))
