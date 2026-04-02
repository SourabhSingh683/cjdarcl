"""
setup_demo_users.py
===================
Run this once to quickly create demo users for all three roles.

Usage:
    cd logistics_project
    python3 manage.py shell < ../setup_demo_users.py

Or run directly:
    python3 setup_demo_users.py
"""

import os
import sys
import django

# ── Bootstrap Django ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'logistics_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_project.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile

DEMO_USERS = [
    {
        "username":   "manager1",
        "password":   "Darcl@1234",
        "first_name": "Rahul",
        "last_name":  "Sharma",
        "email":      "rahul@cjdarcl.com",
        "role":       "manager",
        "vehicle_no": "",
        "customer_id": "",
    },
    {
        "username":   "driver1",
        "password":   "Darcl@1234",
        "first_name": "Suresh",
        "last_name":  "Kumar",
        "email":      "suresh@cjdarcl.com",
        "role":       "driver",
        "vehicle_no": "JH05",   # matches vehicle_no prefix in shipments
        "customer_id": "",
    },
    {
        "username":   "customer1",
        "password":   "Darcl@1234",
        "first_name": "Tata",
        "last_name":  "Steel",
        "email":      "orders@tatasteel.com",
        "role":       "customer",
        "vehicle_no": "",
        "customer_id": "TATA",   # matches customer_name containing "TATA"
    },
]

for u_data in DEMO_USERS:
    user, created = User.objects.get_or_create(username=u_data["username"])
    user.set_password(u_data["password"])
    user.first_name = u_data["first_name"]
    user.last_name = u_data["last_name"]
    user.email = u_data["email"]
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = u_data["role"]
    profile.vehicle_no = u_data["vehicle_no"]
    profile.customer_id = u_data["customer_id"]
    profile.save()

    action = "Created" if created else "Updated"
    print(f"✓ {action}: {u_data['username']} [{u_data['role']}] — password: {u_data['password']}")

print("\n✅ Demo users ready. Login at http://localhost:5173")
print("   Credentials for all users: password = Darcl@1234")
