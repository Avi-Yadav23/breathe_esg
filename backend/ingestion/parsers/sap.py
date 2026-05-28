import csv
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from . import ParseError, NormalizationError
from ..normalizers.flags import (
    BAD_DATE, MISSING_QUANTITY, UNKNOWN_MATERIAL, UNKNOWN_PLANT,
)
from ..normalizers.units import normalize_unit

logger = logging.getLogger(__name__)

PLANT_LOOKUP = {
    "1001": {"name": "Berlin Manufacturing", "country": "DE"},
    "1002": {"name": "Hamburg Distribution", "country": "DE"},
    "1003": {"name": "Munich Office", "country": "DE"},
}

MATERIAL_FUEL_MAP = {
    "FUEL-DI": {"category": "diesel", "scope": 1},
    "FUEL-NG": {"category": "natural_gas", "scope": 1},
    "FUEL-PE": {"category": "petrol", "scope": 1},
    "FUEL-HFO": {"category": "heavy_fuel_oil", "scope": 1},
}

EXPECTED_HEADERS = [
    "Buchungskreis", "Werk", "Belegdatum", "Buchdatum",
    "Material", "Materialbez", "BewArt", "Menge",
    "MengenEinh", "Betrag", "Währung", "Kostenstelle",
]


def parse_sap_file(file_content: bytes) -> list[dict]:
    """
    Parse a SAP ME2M/MB51 tab-delimited export.
    Returns a list of raw row dicts keyed by the English column names.
    Raises ParseError on file-level failures.
    """
    try:
        text = file_content.decode("utf-8-sig")  # handle BOM from Windows exports
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except UnicodeDecodeError as e:
            raise ParseError(f"Cannot decode file: {e}") from e

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")

    # Validate headers exist (flexible: check subset, not exact match)
    try:
        headers = reader.fieldnames
    except Exception as e:
        raise ParseError(f"Cannot read headers: {e}") from e

    if headers is None:
        raise ParseError("File is empty or has no headers")

    rows = []
    for row in reader:
        rows.append(dict(row))

    if not rows:
        raise ParseError("File has headers but no data rows")

    return rows


def normalize_sap_row(raw_row: dict) -> tuple[dict, list[str]]:
    """
    Convert one raw SAP row dict into a normalized record dict.
    Returns (normalized_fields, flag_reasons).
    """
    flags = []
    fields = {
        "source_type": "sap",
        "scope": None,
        "category": "",
        "activity_value": None,
        "activity_unit": "",
        "activity_unit_normalized": "",
        "activity_value_normalized": None,
        "period_start": None,
        "period_end": None,
        "facility_name": "",
        "plant_code": "",
        "location_country": "",
        "flag_reasons": flags,
    }

    # Plant lookup
    plant_code = (raw_row.get("Werk") or "").strip()
    fields["plant_code"] = plant_code
    plant_info = PLANT_LOOKUP.get(plant_code)
    if plant_info:
        fields["facility_name"] = plant_info["name"]
        fields["location_country"] = plant_info["country"]
    elif plant_code:
        flags.append(UNKNOWN_PLANT)

    # Material → category/scope
    material = (raw_row.get("Material") or "").strip()
    fuel_info = MATERIAL_FUEL_MAP.get(material)
    if fuel_info:
        fields["category"] = fuel_info["category"]
        fields["scope"] = fuel_info["scope"]
    elif material:
        flags.append(UNKNOWN_MATERIAL)

    # Date parsing
    date_str = (raw_row.get("Belegdatum") or "").strip()
    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            flags.append(BAD_DATE)
    else:
        flags.append(BAD_DATE)

    fields["period_start"] = parsed_date
    fields["period_end"] = parsed_date

    # Quantity
    menge_str = (raw_row.get("Menge") or "").strip()
    unit_str = (raw_row.get("MengenEinh") or "").strip()
    fields["activity_unit"] = unit_str

    if not menge_str:
        flags.append(MISSING_QUANTITY)
    else:
        try:
            quantity = Decimal(menge_str.replace(",", "."))
            fields["activity_value"] = quantity
            if unit_str:
                try:
                    norm_val, norm_unit = normalize_unit(quantity, unit_str)
                    fields["activity_value_normalized"] = norm_val
                    fields["activity_unit_normalized"] = norm_unit
                except ValueError:
                    from ..normalizers.flags import MISSING_UNIT
                    flags.append(MISSING_UNIT)
            else:
                from ..normalizers.flags import MISSING_UNIT
                flags.append(MISSING_UNIT)
        except InvalidOperation:
            flags.append(MISSING_QUANTITY)

    fields["flag_reasons"] = flags
    return fields, flags
