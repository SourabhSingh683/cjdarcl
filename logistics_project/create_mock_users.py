import os
from pathlib import Path
from dotenv import load_dotenv
import django

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_project.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile

users_data = [
    {"username": "manager1", "role": "manager", "password": "Darcl@1234"},
    {"username": "manager2", "role": "manager", "password": "Darcl@1234"},
    {"username": "driver1", "role": "driver", "password": "Darcl@1234", "vehicle_no": "MH12AB1234"},
    {"username": "customer1", "role": "customer", "password": "Darcl@1234", "customer_id": "CUST001"},
]

for ud in users_data:
    user, created = User.objects.get_or_create(username=ud['username'])
    user.set_password(ud['password'])
    user.is_staff = (ud['role'] == 'manager')
    user.is_superuser = (ud['role'] == 'manager')
    user.save()
    
    profile, p_created = UserProfile.objects.get_or_create(user=user)
    profile.role = ud['role']
    if 'vehicle_no' in ud: profile.vehicle_no = ud['vehicle_no']
    if 'customer_id' in ud: profile.customer_id = ud['customer_id']
    profile.save()
    print(f"Created/Updated {ud['username']} with role {ud['role']}")

print("\nAll mock users generated successfully!")
