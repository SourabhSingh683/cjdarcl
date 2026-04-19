import os
import django
import pandas as pd
import sys

# Setup Django environment
sys.path.append('/Users/sourabhsingh/cjDarcl_project/logistics_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_project.settings')
django.setup()

from shipments.models import Route, Shipment, UploadLog
from shipments.views import _bulk_insert_shipments
from django.contrib.auth.models import User

def test_ingestion():
    # 1. Setup mock data
    user = User.objects.first()
    if not user:
        print("No user found in DB")
        return

    # Create a route with UPPERCASE in DB
    route, _ = Route.objects.get_or_create(origin='TEST_ORIGIN', destination='TEST_DEST')
    print(f"Route in DB: {route.origin} -> {route.destination}")

    # Create a mock upload log
    upload_log = UploadLog.objects.create(file_name="test_upload.xlsx", user=user)

    # 2. Simulate incoming data with Title Case (like data_cleaner would produce)
    data = {
        'shipment_id': ['MOCK_123', 'MOCK_456'],
        'origin': ['Test_Origin', 'Test_Origin'], # Title case
        'destination': ['Test_Dest', 'Test_Dest'], # Title case
        'dispatch_date': [pd.Timestamp.now(), pd.Timestamp.now()],
        'revenue': [1000, 2000],
        'net_weight': [10, 20],
        'vehicle_no': ['V1', 'V2']
    }
    df = pd.DataFrame(data)
    
    # 3. Call optimized insert
    print("Starting bulk insert...")
    _bulk_insert_shipments(df, upload_log, user)
    
    # 4. Verify results
    count = Shipment.objects.filter(upload=upload_log).count()
    print(f"Shipments created for this upload: {count}")
    
    if count == 2:
        print("SUCCESS: Casing mismatch handled correctly.")
    else:
        print("FAILURE: Shipments not created.")

    # Cleanup
    Shipment.objects.filter(upload=upload_log).delete()
    upload_log.delete()

if __name__ == "__main__":
    test_ingestion()
