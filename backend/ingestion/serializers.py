from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Tenant, TenantMembership, IngestionRun, RawRecord, NormalizedRecord, AuditLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug"]


class IngestionRunSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = IngestionRun
        fields = [
            "id", "tenant", "source_type", "uploaded_by", "original_filename",
            "file_hash", "uploaded_at", "status",
            "row_count_total", "row_count_ok", "row_count_flagged", "row_count_error",
            "error_message",
        ]
        read_only_fields = fields


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ["id", "row_number", "raw_data", "parse_error", "created_at"]


class NormalizedRecordSerializer(serializers.ModelSerializer):
    raw_record = RawRecordSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = NormalizedRecord
        fields = [
            "id", "tenant", "ingestion_run", "raw_record",
            "scope", "source_type", "category", "travel_subcategory",
            "activity_value", "activity_unit", "activity_unit_normalized", "activity_value_normalized",
            "period_start", "period_end",
            "facility_name", "plant_code", "location_country",
            "origin_iata", "destination_iata", "travel_class", "distance_km",
            "status", "flag_reasons",
            "reviewed_by", "reviewed_at", "analyst_note",
            "created_at", "updated_at", "is_edited", "locked_at",
        ]
        read_only_fields = [
            "id", "tenant", "ingestion_run", "raw_record",
            "scope", "source_type", "category", "travel_subcategory",
            "reviewed_by", "reviewed_at",
            "created_at", "updated_at", "is_edited", "locked_at",
        ]


class NormalizedRecordEditSerializer(serializers.ModelSerializer):
    """Only the fields an analyst is permitted to change."""
    class Meta:
        model = NormalizedRecord
        fields = ["activity_value", "activity_unit_normalized", "analyst_note"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "action", "actor", "timestamp", "previous_value", "new_value", "note"]
