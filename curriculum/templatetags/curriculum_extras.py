from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except Exception:
        return None


@register.filter
def currency_br(value):
    try:
        amount = Decimal(value)
    except (TypeError, InvalidOperation, ValueError):
        return value
    formatted = f'{amount:.2f}'
    return formatted.replace('.', ',')
