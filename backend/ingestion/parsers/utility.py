import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from . import ParseError
from ..normalizers.flags import (
    DUPLICATE_PERIOD, LONG_BILLING_PERIOD, ZERO_CONSUMPTION, OUTLIER_VALUE,
    MISSING_UNIT,
)
from ..normalizers.flags import check_outlier
from ..normalizers.units import normalize_unit

logger = logging.getLogger(__name__)


def parse_utility_file(file_content: bytes) -> list[dict]:
    """
    Parse a utility portal CSV export.
    Returns list of raw row dicts.
    Raises ParseError on file-level failures.
    """
    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except UnicodeDecodeError as e:
            raise ParseError(f"Cannot decode file: {e}") from e

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ParseError("File is empty or has no headers")

    rows = [dict(r) for r in reader]
    if not rows:
        raise ParseError("File has headers but no data rows")
    return rows


def normalize_utility_rows(raw_rows: list[dict], existing_meter_periods: set) -> list[tuple[dict, list[str]]]:
    """
    Normalize all rows from one utility file together so outlier detection
    can compare values across rows within this run.

    existing_meter_periods: set of (facility_name, period_start_str, period_end_str) tuples
    already in the database for this tenant — used for duplicate detection.

    Returns list of (normalized_fields, flags) tuples.
    """
    # Collect values per meter for outlier detection
    meter_values: dict[str, list] = {}
    parsed_rows = []

    for raw_row in raw_rows:
        meter_id = (raw_row.get("meter_id") or "").strip()
        consumption_str = (raw_row.get("consumption_kwh") or "").strip()
        try:
            consumption = Decimal(consumption_str) if consumption_str else None
        except InvalidOperation:
            consumption = None
        if meter_id and consumption is not None:
            meter_values.setdefault(meter_id, []).append(consumption)
        parsed_rows.append((raw_row, meter_id, consumption))

    results = []
    seen_this_run = set()

    for raw_row, meter_id, consumption in parsed_rows:
        flags = []
        facility_name = (raw_row.get("facility_name") or "").strip()
        fields = {
            "source_type": "utility",
            "scope": 2,
            "category": "electricity",
            "activity_value": None,
            "activity_unit": "kWh",
            "activity_unit_normalized": "kwh",
            "activity_value_normalized": None,
            "period_start": None,
            "period_end": None,
            "facility_name": facility_name,
            "plant_code": "",
            "location_country": "",
            "flag_reasons": flags,
        }

        # Parse billing period
        start_str = (raw_row.get("billing_period_start") or "").strip()
        end_str = (raw_row.get("billing_period_end") or "").strip()
        period_start = None
        period_end = None

        try:
            period_start = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
        except ValueError:
            from ..normalizers.flags import BAD_DATE
            flags.append(BAD_DATE)
        try:
            period_end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
        except ValueError:
            from ..normalizers.flags import BAD_DATE
            if BAD_DATE not in flags:
                flags.append(BAD_DATE)

        fields["period_start"] = period_start
        fields["period_end"] = period_end

        if period_start and period_end:
            delta = (period_end - period_start).days
            if delta > 45:
                flags.append(LONG_BILLING_PERIOD)

            # Duplicate detection — within run and against existing records
            # Key uses facility_name + period dates since meter_id is not stored on NormalizedRecord
            key = (facility_name, str(period_start), str(period_end))
            if key in seen_this_run or key in existing_meter_periods:
                flags.append(DUPLICATE_PERIOD)
            else:
                seen_this_run.add(key)

        # Consumption value
        if consumption is None:
            from ..normalizers.flags import MISSING_QUANTITY
            flags.append(MISSING_QUANTITY)
        elif consumption == 0:
            flags.append(ZERO_CONSUMPTION)
            fields["activity_value"] = consumption
            fields["activity_value_normalized"] = consumption
        else:
            fields["activity_value"] = consumption
            fields["activity_value_normalized"] = consumption

            # Outlier detection across this meter's values in this run
            peer_values = meter_values.get(meter_id, [])
            if len(peer_values) > 1 and check_outlier(consumption, peer_values):
                flags.append(OUTLIER_VALUE)

        fields["flag_reasons"] = flags
        results.append((fields, flags))

    return results
