import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_project.settings')
django.setup()

from shipments.models import Shipment

# Delete the mock shipments created before the real data was loaded
deleted_count, _ = Shipment.objects.filter(transporter_name__icontains='SONS').delete()
print(f"Deleted {deleted_count} mock shipments.")
