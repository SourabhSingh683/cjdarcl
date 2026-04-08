import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_project.settings')
django.setup()

from shipments.models import Shipment

transporters = list(Shipment.objects.values_list('transporter_name', flat=True).distinct())
print("===TRANSPORTERS===")
for t in transporters:
    print(t)
print("===END===")
