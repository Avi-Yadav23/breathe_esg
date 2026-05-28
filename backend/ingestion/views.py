import hashlib
import logging
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException

from .models import (
    Tenant, TenantMembership, IngestionRun, RawRecord, NormalizedRecord, AuditLog
)
from .serializers import (
    UserSerializer, TenantSerializer, IngestionRunSerializer,
    NormalizedRecordSerializer, NormalizedRecordEditSerializer, AuditLogSerializer
)
from .parsers import ParseError, NormalizationError
from .parsers.sap import parse_sap_file, normalize_sap_row
from .parsers.utility import parse_utility_file, normalize_utility_rows
from .parsers.travel import parse_travel_file, normalize_travel_rows

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is not None:
        error_msg = str(exc)
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                error_msg = "; ".join(f"{k}: {v}" for k, v in exc.detail.items())
            else:
                error_msg = str(exc.detail)
        response.data = {"error": error_msg, "detail": response.data}
    return response


def get_user_tenant(user):
    """Return the first tenant this user belongs to. Raises PermissionDenied if none."""
    membership = TenantMembership.objects.filter(user=user).select_related("tenant").first()
    if not membership:
        raise PermissionDenied("User does not belong to any tenant.")
    return membership.tenant


class RecordsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"error": "username and password required"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": {"id": user.id, "email": user.email, "username": user.username},
        })


class LogoutView(APIView):
    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({"detail": "Logged out"})


class MeView(APIView):
    def get(self, request):
        user = request.user
        try:
            tenant = get_user_tenant(user)
            tenant_data = TenantSerializer(tenant).data
        except PermissionDenied:
            tenant_data = None
        return Response({
            "user": UserSerializer(user).data,
            "tenant": tenant_data,
        })


class UploadView(APIView):
    def post(self, request):
        tenant = get_user_tenant(request.user)
        source_type = request.data.get("source_type")
        if source_type not in ("sap", "utility", "travel"):
            return Response({"error": "source_type must be sap, utility, or travel"}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        file_content = uploaded_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Dedup: reject exact same file content for this tenant
        if IngestionRun.objects.filter(tenant=tenant, file_hash=file_hash).exists():
            return Response({"error": "This file has already been uploaded (duplicate hash)"}, status=status.HTTP_409_CONFLICT)

        run = IngestionRun.objects.create(
            tenant=tenant,
            source_type=source_type,
            uploaded_by=request.user,
            original_filename=uploaded_file.name,
            file_hash=file_hash,
            status="processing",
        )

        try:
            _process_ingestion(run, source_type, file_content, tenant, request.user)
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.save()
            logger.error("Ingestion run %s failed: %s", run.id, e, exc_info=True)
            return Response({
                "error": f"Ingestion failed: {e}",
                "ingestion_run_id": str(run.id),
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response({
            "ingestion_run_id": str(run.id),
            "row_count_total": run.row_count_total,
            "row_count_ok": run.row_count_ok,
            "row_count_flagged": run.row_count_flagged,
            "row_count_error": run.row_count_error,
        }, status=status.HTTP_201_CREATED)


def _process_ingestion(run: IngestionRun, source_type: str, file_content: bytes, tenant, user):
    """
    Synchronous ingestion: parse file → create RawRecords → normalize → create NormalizedRecords.
    Updates run counters and status.
    """
    if source_type == "sap":
        raw_rows = parse_sap_file(file_content)
        normalized_pairs = [normalize_sap_row(r) for r in raw_rows]
        # results is list of ((fields, flags), raw_row)
        results = list(zip(normalized_pairs, raw_rows))

    elif source_type == "utility":
        raw_rows = parse_utility_file(file_content)
        # Build existing (facility_name, period_start, period_end) set for duplicate detection.
        # meter_id is not stored on NormalizedRecord, so we key on facility_name + period dates.
        existing_meter_periods = set()
        for rec in NormalizedRecord.objects.filter(
            tenant=tenant, source_type="utility"
        ).values("facility_name", "period_start", "period_end"):
            existing_meter_periods.add((
                rec["facility_name"] or "",
                str(rec["period_start"]) if rec["period_start"] else "",
                str(rec["period_end"]) if rec["period_end"] else "",
            ))
        normalized_list = normalize_utility_rows(raw_rows, existing_meter_periods)
        results = list(zip(normalized_list, raw_rows))

    elif source_type == "travel":
        raw_rows = parse_travel_file(file_content)
        normalized_list = normalize_travel_rows(raw_rows)
        results = list(zip(normalized_list, raw_rows))

    else:
        raise ParseError(f"Unknown source_type: {source_type}")

    ok = flagged = error = 0

    # Use enumerate to get row numbers without O(n^2) list.index() calls
    for idx, ((fields, flags), raw_row) in enumerate(results):
        raw_record = RawRecord.objects.create(
            ingestion_run=run,
            row_number=idx + 1,  # 1-indexed to match source file line numbers
            raw_data=raw_row,
            parse_error="",
        )

        rec_status = "pending"
        if flags:
            rec_status = "flagged"
            flagged += 1
        else:
            ok += 1

        norm = NormalizedRecord.objects.create(
            tenant=tenant,
            ingestion_run=run,
            raw_record=raw_record,
            scope=fields.get("scope"),
            source_type=source_type,
            category=fields.get("category", ""),
            travel_subcategory=fields.get("travel_subcategory", ""),
            activity_value=fields.get("activity_value"),
            activity_unit=fields.get("activity_unit", ""),
            activity_unit_normalized=fields.get("activity_unit_normalized", ""),
            activity_value_normalized=fields.get("activity_value_normalized"),
            period_start=fields.get("period_start"),
            period_end=fields.get("period_end"),
            facility_name=fields.get("facility_name", ""),
            plant_code=fields.get("plant_code", ""),
            location_country=fields.get("location_country", ""),
            origin_iata=fields.get("origin_iata", ""),
            destination_iata=fields.get("destination_iata", ""),
            travel_class=fields.get("travel_class", ""),
            distance_km=fields.get("distance_km"),
            status=rec_status,
            flag_reasons=flags,
        )

        AuditLog.objects.create(
            normalized_record=norm,
            action="created",
            actor=user,
            new_value={"status": rec_status, "flag_reasons": flags},
        )

    run.row_count_total = len(results)
    run.row_count_ok = ok
    run.row_count_flagged = flagged
    run.row_count_error = error
    run.status = "complete"
    run.save()


class IngestionRunListView(APIView):
    def get(self, request):
        tenant = get_user_tenant(request.user)
        qs = IngestionRun.objects.filter(tenant=tenant).order_by("-uploaded_at")
        source_type = request.query_params.get("source_type")
        status_filter = request.query_params.get("status")
        if source_type:
            qs = qs.filter(source_type=source_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = RecordsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(IngestionRunSerializer(page, many=True).data)


class IngestionRunDetailView(APIView):
    def get(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            run = IngestionRun.objects.get(pk=pk, tenant=tenant)
        except IngestionRun.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(IngestionRunSerializer(run).data)


class NormalizedRecordListView(APIView):
    def get(self, request):
        tenant = get_user_tenant(request.user)
        qs = NormalizedRecord.objects.filter(tenant=tenant).select_related(
            "raw_record", "reviewed_by", "ingestion_run"
        )
        # Filters
        for param, field in [
            ("scope", "scope"), ("source_type", "source_type"),
            ("status", "status"), ("ingestion_run", "ingestion_run__id"),
        ]:
            val = request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})

        start_after = request.query_params.get("period_start_after")
        start_before = request.query_params.get("period_start_before")
        if start_after:
            qs = qs.filter(period_start__gte=start_after)
        if start_before:
            qs = qs.filter(period_start__lte=start_before)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(facility_name__icontains=search) |
                Q(plant_code__icontains=search) |
                Q(category__icontains=search)
            )

        paginator = RecordsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(NormalizedRecordSerializer(page, many=True).data)


class NormalizedRecordDetailView(APIView):
    def get(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            rec = NormalizedRecord.objects.get(pk=pk, tenant=tenant)
        except NormalizedRecord.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(NormalizedRecordSerializer(rec).data)

    def patch(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            rec = NormalizedRecord.objects.get(pk=pk, tenant=tenant)
        except NormalizedRecord.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if rec.locked_at:
            return Response({"error": "Record is locked for audit and cannot be edited"}, status=status.HTTP_403_FORBIDDEN)

        serializer = NormalizedRecordEditSerializer(rec, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        prev = {
            "activity_value": str(rec.activity_value) if rec.activity_value else None,
            "activity_unit_normalized": rec.activity_unit_normalized,
            "analyst_note": rec.analyst_note,
        }

        serializer.save(is_edited=True)

        # Re-read from the updated instance (serializer.save() mutates in place)
        new = {
            "activity_value": str(rec.activity_value) if rec.activity_value else None,
            "activity_unit_normalized": rec.activity_unit_normalized,
            "analyst_note": rec.analyst_note,
        }

        AuditLog.objects.create(
            normalized_record=rec,
            action="value_edited",
            actor=request.user,
            previous_value=prev,
            new_value=new,
        )

        return Response(NormalizedRecordSerializer(rec).data)


class RecordApproveView(APIView):
    def post(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            rec = NormalizedRecord.objects.get(pk=pk, tenant=tenant)
        except NormalizedRecord.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if rec.locked_at:
            return Response({"error": "Record is already locked"}, status=status.HTTP_400_BAD_REQUEST)

        prev_status = rec.status
        rec.status = "approved"
        rec.reviewed_by = request.user
        rec.reviewed_at = timezone.now()
        rec.locked_at = timezone.now()
        rec.save()

        AuditLog.objects.create(
            normalized_record=rec,
            action="locked",
            actor=request.user,
            previous_value={"status": prev_status},
            new_value={"status": "approved"},
        )
        return Response(NormalizedRecordSerializer(rec).data)


class RecordRejectView(APIView):
    def post(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            rec = NormalizedRecord.objects.get(pk=pk, tenant=tenant)
        except NormalizedRecord.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if rec.locked_at:
            return Response({"error": "Record is locked and cannot be rejected"}, status=status.HTTP_400_BAD_REQUEST)

        note = request.data.get("note", "")
        prev_status = rec.status
        rec.status = "rejected"
        rec.reviewed_by = request.user
        rec.reviewed_at = timezone.now()
        if note:
            rec.analyst_note = note
        rec.save()

        AuditLog.objects.create(
            normalized_record=rec,
            action="status_changed",
            actor=request.user,
            previous_value={"status": prev_status},
            new_value={"status": "rejected"},
            note=note,
        )
        return Response(NormalizedRecordSerializer(rec).data)


class RecordFlagView(APIView):
    def post(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            rec = NormalizedRecord.objects.get(pk=pk, tenant=tenant)
        except NormalizedRecord.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if rec.locked_at:
            return Response({"error": "Record is locked"}, status=status.HTTP_400_BAD_REQUEST)

        note = request.data.get("note", "")
        extra_flags = request.data.get("flag_reasons", [])
        prev_status = rec.status
        rec.status = "flagged"
        rec.flag_reasons = list(set(rec.flag_reasons + extra_flags))
        if note:
            rec.analyst_note = note
        rec.save()

        AuditLog.objects.create(
            normalized_record=rec,
            action="status_changed",
            actor=request.user,
            previous_value={"status": prev_status},
            new_value={"status": "flagged", "flag_reasons": rec.flag_reasons},
            note=note,
        )
        return Response(NormalizedRecordSerializer(rec).data)


class BulkApproveView(APIView):
    def post(self, request):
        tenant = get_user_tenant(request.user)
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"error": "ids list required"}, status=status.HTTP_400_BAD_REQUEST)

        records = NormalizedRecord.objects.filter(pk__in=ids, tenant=tenant, locked_at__isnull=True)
        now = timezone.now()
        updated = 0
        for rec in records:
            prev = rec.status
            rec.status = "approved"
            rec.reviewed_by = request.user
            rec.reviewed_at = now
            rec.locked_at = now
            rec.save()
            AuditLog.objects.create(
                normalized_record=rec,
                action="locked",
                actor=request.user,
                previous_value={"status": prev},
                new_value={"status": "approved"},
            )
            updated += 1

        return Response({"updated": updated})


class BulkRejectView(APIView):
    def post(self, request):
        tenant = get_user_tenant(request.user)
        ids = request.data.get("ids", [])
        note = request.data.get("note", "")
        if not ids:
            return Response({"error": "ids list required"}, status=status.HTTP_400_BAD_REQUEST)

        records = NormalizedRecord.objects.filter(pk__in=ids, tenant=tenant, locked_at__isnull=True)
        now = timezone.now()
        updated = 0
        for rec in records:
            prev = rec.status
            rec.status = "rejected"
            rec.reviewed_by = request.user
            rec.reviewed_at = now
            if note:
                rec.analyst_note = note
            rec.save()
            AuditLog.objects.create(
                normalized_record=rec,
                action="status_changed",
                actor=request.user,
                previous_value={"status": prev},
                new_value={"status": "rejected"},
                note=note,
            )
            updated += 1

        return Response({"updated": updated})


class DashboardSummaryView(APIView):
    def get(self, request):
        tenant = get_user_tenant(request.user)
        qs = NormalizedRecord.objects.filter(tenant=tenant)

        total = qs.count()
        by_status = {s: qs.filter(status=s).count() for s in ["pending", "flagged", "approved", "rejected", "error"]}
        by_scope = {str(s): qs.filter(scope=s).count() for s in [1, 2, 3]}
        by_source = {st: qs.filter(source_type=st).count() for st in ["sap", "utility", "travel"]}

        recent_runs = IngestionRun.objects.filter(tenant=tenant).order_by("-uploaded_at")[:5]

        return Response({
            "total_records": total,
            "pending": by_status["pending"],
            "flagged": by_status["flagged"],
            "approved": by_status["approved"],
            "rejected": by_status["rejected"],
            "error": by_status["error"],
            "by_scope": by_scope,
            "by_source": by_source,
            "recent_runs": IngestionRunSerializer(recent_runs, many=True).data,
        })


class RecordAuditView(APIView):
    def get(self, request, pk):
        tenant = get_user_tenant(request.user)
        try:
            rec = NormalizedRecord.objects.get(pk=pk, tenant=tenant)
        except NormalizedRecord.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        logs = rec.audit_logs.select_related("actor").all()
        return Response(AuditLogSerializer(logs, many=True).data)
