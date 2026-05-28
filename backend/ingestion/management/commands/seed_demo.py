import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from ingestion.models import Tenant, TenantMembership, IngestionRun
from ingestion.parsers.sap import parse_sap_file, normalize_sap_row
from ingestion.parsers.utility import parse_utility_file, normalize_utility_rows
from ingestion.parsers.travel import parse_travel_file, normalize_travel_rows
from ingestion.models import RawRecord, NormalizedRecord, AuditLog
import hashlib


class Command(BaseCommand):
    help = "Seed demo data: Acme Corp tenant, analyst user, and runs all sample fixtures"

    def handle(self, *args, **options):
        # Create tenant
        tenant, _ = Tenant.objects.get_or_create(
            slug="acme",
            defaults={"name": "Acme Corp"},
        )
        self.stdout.write(f"Tenant: {tenant.name} ({tenant.slug})")

        # Create analyst user
        user, created = User.objects.get_or_create(username="analyst")
        if created:
            user.set_password("demo1234")
            user.email = "analyst@acme.com"
            user.save()
        token, _ = Token.objects.get_or_create(user=user)

        TenantMembership.objects.get_or_create(
            user=user, tenant=tenant,
            defaults={"role": "analyst"},
        )

        self.stdout.write(f"User: analyst / demo1234")
        self.stdout.write(f"Token: {token.key}")

        # Run sample fixtures
        fixtures_dir = Path(__file__).resolve().parent.parent.parent / "fixtures"

        sap_file = fixtures_dir / "sample_sap.txt"
        utility_file = fixtures_dir / "sample_utility.csv"
        travel_file = fixtures_dir / "sample_travel.csv"

        for filepath, source_type in [
            (sap_file, "sap"),
            (utility_file, "utility"),
            (travel_file, "travel"),
        ]:
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"Fixture not found: {filepath}"))
                continue

            content = filepath.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()

            if IngestionRun.objects.filter(tenant=tenant, file_hash=file_hash).exists():
                self.stdout.write(f"Skipping {source_type} (already seeded)")
                continue

            run = IngestionRun.objects.create(
                tenant=tenant,
                source_type=source_type,
                uploaded_by=user,
                original_filename=filepath.name,
                file_hash=file_hash,
                status="processing",
            )

            try:
                from ingestion.views import _process_ingestion
                _process_ingestion(run, source_type, content, tenant, user)
                self.stdout.write(self.style.SUCCESS(
                    f"Seeded {source_type}: {run.row_count_total} rows "
                    f"({run.row_count_ok} ok, {run.row_count_flagged} flagged, {run.row_count_error} error)"
                ))
            except Exception as e:
                run.status = "failed"
                run.error_message = str(e)
                run.save()
                self.stdout.write(self.style.ERROR(f"Failed {source_type}: {e}"))

        self.stdout.write(self.style.SUCCESS("\nDemo seeded. Login: analyst / demo1234"))
