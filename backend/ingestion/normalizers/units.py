import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

UNIT_NORMALIZATION = {
    "L": ("liters", Decimal("1.0")),
    "l": ("liters", Decimal("1.0")),
    "LTR": ("liters", Decimal("1.0")),
    "GAL": ("liters", Decimal("3.78541")),
    "GL": ("liters", Decimal("3.78541")),
    "m3": ("cubic_meters", Decimal("1.0")),
    "M3": ("cubic_meters", Decimal("1.0")),
    "CCF": ("cubic_meters", Decimal("2.8317")),
    "MCF": ("cubic_meters", Decimal("28.317")),
    "MMBTU": ("mmbtu", Decimal("1.0")),
    "kWh": ("kwh", Decimal("1.0")),
    "KWH": ("kwh", Decimal("1.0")),
    "MWh": ("kwh", Decimal("1000.0")),
    "GWh": ("kwh", Decimal("1000000.0")),
    "kg": ("kilograms", Decimal("1.0")),
    "KG": ("kilograms", Decimal("1.0")),
    "t": ("kilograms", Decimal("1000.0")),
    "MT": ("kilograms", Decimal("1000.0")),
    "lb": ("kilograms", Decimal("0.453592")),
    "km": ("km", Decimal("1.0")),
    "mi": ("km", Decimal("1.60934")),
    "nights": ("nights", Decimal("1.0")),
}


def normalize_unit(value, unit):
    """
    Convert value+unit to canonical unit within the same physical quantity.
    Returns (normalized_value, canonical_unit_name) or raises ValueError
    if unit is unknown.
    """
    if not unit:
        raise ValueError("unit is blank")

    mapping = UNIT_NORMALIZATION.get(unit)
    if mapping is None:
        raise ValueError(f"unknown unit: {unit!r}")

    canonical_name, factor = mapping
    normalized_value = Decimal(str(value)) * factor
    return normalized_value, canonical_name
