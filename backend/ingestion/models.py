import uuid
from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """Multi-tenancy root. Each enterprise client is a Tenant."""
    # UUID prevents sequential ID enumeration across tenants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    # slug used in URLs and API paths to avoid exposing UUID in frontend routes
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    """Links Django users to Tenants with a role."""
    ROLE_CHOICES = [("admin", "Admin"), ("analyst", "Analyst"), ("viewer", "Viewer")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="members")
    # role stored here (not on User) so the same user can be analyst in one tenant and viewer in another
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="analyst")

    class Meta:
        unique_together = ("user", "tenant")


class IngestionRun(models.Model):
    """
    One file upload = one IngestionRun.
    Tracks provenance: who uploaded what file for which tenant, when.
    """
    SOURCE_TYPES = [
        ("sap", "SAP Fuel & Procurement"),
        ("utility", "Utility Electricity"),
        ("travel", "Corporate Travel"),
    ]
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="ingestion_runs")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    original_filename = models.CharField(max_length=255)
    # SHA-256 hash of file content — used to reject duplicate file submissions
    file_hash = models.CharField(max_length=64)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    # denormalized counts so the runs list view avoids COUNT() queries
    row_count_total = models.IntegerField(default=0)
    row_count_ok = models.IntegerField(default=0)
    row_count_flagged = models.IntegerField(default=0)
    row_count_error = models.IntegerField(default=0)
    # stores the top-level failure message if the entire file failed to parse
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tenant} / {self.source_type} / {self.uploaded_at:%Y-%m-%d}"


class RawRecord(models.Model):
    """
    One row from the uploaded file, stored verbatim as JSON.
    Never mutated after creation — source of truth for what actually came in.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="raw_records")
    # 1-indexed to match line numbers visible to users in their source files
    row_number = models.IntegerField()
    # verbatim parsed dict — enables audit and re-normalization without re-uploading
    raw_data = models.JSONField()
    # populated only when a row can't be parsed at all (e.g. wrong number of columns)
    parse_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]


class NormalizedRecord(models.Model):
    """
    The canonical emissions activity record.
    One NormalizedRecord per RawRecord (1:1). If a raw row couldn't be normalized,
    NormalizedRecord is created with status='error'.

    Scope definitions (GHG Protocol):
      Scope 1 — Direct emissions (fuel combustion)
      Scope 2 — Indirect from purchased electricity
      Scope 3 — Value chain (business travel = category 6)
    """
    SCOPE_CHOICES = [(1, "Scope 1"), (2, "Scope 2"), (3, "Scope 3")]
    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("flagged", "Flagged — Needs Attention"),
        ("error", "Parse/Normalization Error"),
    ]
    TRAVEL_CATEGORY_CHOICES = [
        ("flight", "Flight"),
        ("hotel", "Hotel"),
        ("ground", "Ground Transport"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="normalized_records")
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="normalized_records")
    # OneToOne enforces exactly one normalized output per raw input — no silent drops
    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name="normalized")

    # Classification
    scope = models.IntegerField(choices=SCOPE_CHOICES, null=True, blank=True)
    source_type = models.CharField(max_length=20)
    # e.g. "diesel", "natural_gas", "electricity", "flight", "hotel" — feeds emission factor lookup
    category = models.CharField(max_length=50, blank=True)
    travel_subcategory = models.CharField(max_length=20, choices=TRAVEL_CATEGORY_CHOICES, blank=True)

    # Activity data — normalized
    activity_value = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    # as-received unit preserved for analyst review and dedup of normalization errors
    activity_unit = models.CharField(max_length=30, blank=True)
    # canonical unit after normalization — what the emissions engine will consume
    activity_unit_normalized = models.CharField(max_length=30, blank=True)
    activity_value_normalized = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    # Time period
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Location / facility
    facility_name = models.CharField(max_length=255, blank=True)
    # SAP Werk code — needed to look up plant metadata from client's org data
    plant_code = models.CharField(max_length=50, blank=True)
    # ISO 3166-1 alpha-2 — enables country-level grid emission factor selection
    location_country = models.CharField(max_length=2, blank=True)

    # Travel-specific
    origin_iata = models.CharField(max_length=3, blank=True)
    destination_iata = models.CharField(max_length=3, blank=True)
    # travel class determines emission factor multiplier (business ~2x economy)
    travel_class = models.CharField(max_length=20, blank=True)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    # list of flag reason strings — drives analyst triage queue
    flag_reasons = models.JSONField(default=list)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_records")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    analyst_note = models.TextField(blank=True)

    # Audit / lineage
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # tracks post-normalization edits so downstream consumers know the value was human-adjusted
    is_edited = models.BooleanField(default=False)
    # once set, application layer rejects further edits — protects audit submission integrity
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-ingestion_run__uploaded_at", "raw_record__row_number"]


class AuditLog(models.Model):
    """
    Append-only log. Every status change, edit, approval, rejection writes one row.
    Never deleted.
    """
    ACTION_CHOICES = [
        ("created", "Record Created"),
        ("status_changed", "Status Changed"),
        ("value_edited", "Value Edited"),
        ("note_added", "Note Added"),
        ("locked", "Locked for Audit"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    normalized_record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    # snapshot of the fields that changed — supports point-in-time reconstruction
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["timestamp"]
