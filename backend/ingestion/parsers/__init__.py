class ParseError(Exception):
    """Raised when a file-level parse failure occurs (e.g. wrong delimiter, missing header)."""
    pass


class NormalizationError(Exception):
    """Raised when a row-level normalization fails in an unexpected way."""
    pass
