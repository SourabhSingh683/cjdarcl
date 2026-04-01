import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_project.settings')
django.setup()

from shipments.models import Shipment
from django.db.models import F

updated1 = Shipment.objects.filter(revenue=0, total_amount__gt=0).update(revenue=F('total_amount'))
updated2 = Shipment.objects.filter(revenue=0, net_weight__gt=0, rate_per_mt__gt=0).update(revenue=F('net_weight') * F('rate_per_mt'))

print(f"Updated {updated1} records using total_amount")
print(f"Updated {updated2} records using net_weight * rate_per_mt")
