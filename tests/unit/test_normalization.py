import pytest
from src.llm.normalization import normalize_digits, normalize_decimal, normalize_date

def test_normalize_digits():
    # standard digits
    assert normalize_digits("12345.67") == "12345.67"
    # arabic-indic
    assert normalize_digits("١٢٣٤٥.٦٧") == "12345.67"
    # extended arabic-indic
    assert normalize_digits("۱۲۳۴۵.۶۷") == "12345.67"
    # arabic decimal and thousand separators
    assert normalize_digits("١٢٬٣٤٥٫٦٧") == "12,345.67"
    # None and empty
    assert normalize_digits(None) is None
    assert normalize_digits("") == ""

def test_normalize_decimal():
    # Standard format
    assert normalize_decimal("12345.67") == 12345.67
    assert normalize_decimal("12,345.67") == 12345.67
    # European format
    assert normalize_decimal("12.345,67") == 12345.67
    assert normalize_decimal("1.234,56") == 1234.56
    assert normalize_decimal("123,45") == 123.45
    # Arabic text translated to digits
    assert normalize_decimal("١٢٬٣٤٥٫٦٧") == 12345.67
    # Space separator
    assert normalize_decimal("12 345.67") == 12345.67
    assert normalize_decimal("12 345,67") == 12345.67
    # Edge cases
    assert normalize_decimal("") == 0.0
    assert normalize_decimal(None) == 0.0
    assert normalize_decimal("invalid") == 0.0

def test_normalize_date():
    # standard
    assert normalize_date("2026-10-04") == "2026-10-04"
    # slash date
    assert normalize_date("04/10/2026") == "2026-10-04"
    # arabic-indic slash date
    assert normalize_date("٠٤/١٠/٢٠٢٦") == "2026-10-04"
    # text
    assert normalize_date("4 Oct 2026") == "2026-10-04"
    assert normalize_date("October 4, 2026") == "2026-10-04"
    # Edge cases
    assert normalize_date(None) is None
    assert normalize_date("") == ""
    assert normalize_date("not a date") == "not a date"
