from decimal import Decimal
from statistics import median

# All valid flag reason strings
MISSING_QUANTITY = "missing_quantity"
MISSING_UNIT = "missing_unit"
BAD_DATE = "bad_date"
UNKNOWN_MATERIAL = "unknown_material"
UNIT_AMBIGUOUS = "unit_ambiguous"
DUPLICATE_PERIOD = "duplicate_period"
LONG_BILLING_PERIOD = "long_billing_period"
ZERO_CONSUMPTION = "zero_consumption"
OUTLIER_VALUE = "outlier_value"
UNKNOWN_AIRPORT = "unknown_airport"
MISSING_DESTINATION = "missing_destination"
MISSING_TRAVEL_CLASS = "missing_travel_class"
MISSING_DISTANCE = "missing_distance"
UNKNOWN_PLANT = "unknown_plant"


def check_outlier(value, all_values, multiplier=3):
    """Return True if value > multiplier * median(all_values)."""
    if not all_values or value is None:
        return False
    med = median([Decimal(str(v)) for v in all_values if v is not None])
    if med == 0:
        return False
    return Decimal(str(value)) > multiplier * med
