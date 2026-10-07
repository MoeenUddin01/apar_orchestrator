import re
from typing import Optional
from dateutil import parser

def normalize_digits(text: str) -> str:
    """Converts Arabic-Indic and Extended Arabic-Indic digits to standard ASCII numerals."""
    if not text:
        return text
        
    translation_table = text.maketrans(
        '٠١٢٣٤٥٦٧٨٩' + '۰۱۲۳۴۵۶۷۸۹',
        '0123456789' + '0123456789'
    )
    # Also replace Arabic decimal separator (٫) U+066B and thousands separator (٬) U+066C
    text = text.translate(translation_table)
    text = text.replace('٫', '.').replace('٬', ',')
    return text

def normalize_decimal(value: str) -> float:
    """Normalizes regional number formats into standard floating-point representation."""
    if not value:
        return 0.0
        
    value = str(value)
    value = normalize_digits(value).strip()
    
    # Remove spaces used as thousand separators (e.g., 12 345.67)
    value = re.sub(r'(?<=\d)\s+(?=\d)', '', value)
    
    # If the format is European like 12.345,67
    # Check if comma is the last separator and dot appears before it
    if ',' in value and '.' in value:
        last_comma = value.rfind(',')
        last_dot = value.rfind('.')
        if last_comma > last_dot:
            # Format: 1.234,56 -> 1234.56
            value = value.replace('.', '')
            value = value.replace(',', '.')
        else:
            # Format: 1,234.56 -> 1234.56
            value = value.replace(',', '')
    elif ',' in value and '.' not in value:
        # Check if comma is used as decimal or thousand
        # If there are exactly two digits after comma, it's likely a decimal
        if re.search(r',\d{1,2}$', value):
            value = value.replace(',', '.')
        else:
            # E.g. 1,000
            value = value.replace(',', '')
            
    # Remove any remaining commas just in case it was missed
    value = value.replace(',', '')
    
    try:
        return float(value)
    except ValueError:
        return 0.0

def normalize_date(date_str: str) -> Optional[str]:
    """Parses localized date strings into ISO 8601 YYYY-MM-DD standard format."""
    if not date_str:
        return date_str
        
    date_str = str(date_str)
    date_str = normalize_digits(date_str)
    
    # If it already looks like YYYY-MM-DD, try parsing with yearfirst
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", date_str):
        dayfirst = False
        yearfirst = True
    else:
        dayfirst = True
        yearfirst = False
        
    try:
        parsed_date = parser.parse(date_str, dayfirst=dayfirst, yearfirst=yearfirst)
        return parsed_date.strftime("%Y-%m-%d")
    except Exception:
        # Fallback to the original if parsing fails
        return date_str
