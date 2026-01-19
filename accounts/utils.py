import re

import phonenumbers


def normalize_whatsapp_number(value: str, default_region: str = 'BR') -> str:
    """
    Normaliza para formato E.164 sempre que possível (ex: +5511999999999).
    Se não conseguir validar, retorna dígitos limpos ou string vazia.
    """
    if not value:
        return ''

    raw = re.sub(r'[^\d+]', '', str(value)).strip()
    try:
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    digits = re.sub(r'\D', '', str(value))
    if not digits:
        return ''

    if not digits.startswith('0') and len(digits) >= 10:
        return f'+{digits}'

    return digits
