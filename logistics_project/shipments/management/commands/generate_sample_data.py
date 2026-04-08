"""
Management command to import real data from an Excel file into the database.
Usage: python manage.py generate_sample_data [--file "SAP_Consignment_Overview (96).xlsx"]
"""

import os
import time
from django.core.management.base import BaseCommand
from shipments.models import UploadLog
from shipments.utils.data_cleaner import process_file
from shipments.views import _bulk_insert_shipments


class Command(BaseCommand):
    help = "Import real Excel data into the database instead of generating random data."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default="SAP_Consignment_Overview (96).xlsx", help="Real Excel file to import")

    def handle(self, *args, **options):
        file_path = options["file"]
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        file_name = os.path.basename(file_path)
        self.stdout.write(self.style.WARNING(f"Processing real data from: {file_name}..."))
        
        upload_log = UploadLog.objects.create(
            file_name=file_name, status=UploadLog.Status.PROCESSING,
        )
        start_time = time.time()
        
        try:
            with open(file_path, "rb") as f:
                clean_df, errors, dup_count = process_file(f, file_name)
            
            self.stdout.write(self.style.WARNING(f"Cleaned {len(clean_df)} rows. Inserting into database..."))
            _bulk_insert_shipments(clean_df, upload_log)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            upload_log.total_rows = len(clean_df) + len(errors) + dup_count
            upload_log.processed_rows = len(clean_df)
            upload_log.error_rows = len(errors)
            upload_log.duplicate_rows = dup_count
            upload_log.processing_time_ms = elapsed_ms
            upload_log.status = UploadLog.Status.COMPLETED if not errors else UploadLog.Status.PARTIAL
            upload_log.save()
            
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {len(clean_df)} rows from {file_name} in {elapsed_ms}ms!"))
            
        except Exception as e:
            upload_log.status = UploadLog.Status.FAILED
            upload_log.save()
            self.stdout.write(self.style.ERROR(f"Failed to process file: {str(e)}"))
