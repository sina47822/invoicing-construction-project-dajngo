# core/sooratvaziat/templatetags/number_extras.py
from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()

@register.filter(name='floatvalue')
def floatvalue(value):
    """
    Convert value to a float-like number for template arithmetic (returns Decimal).
    Returns Decimal(0) on invalid input.
    Use Decimal for money-like values to reduce floating point issues.
    """
    if value is None:
        return Decimal('0')
    # if already Decimal or int/float, return Decimal
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return Decimal('0')
    # assume string: remove common thousands separators and whitespace
    try:
        s = str(value).strip()
        # remove commas and non-breaking spaces used as thousands separators
        s = s.replace(',', '').replace('\u00A0', '').replace('\u200F', '')
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')
