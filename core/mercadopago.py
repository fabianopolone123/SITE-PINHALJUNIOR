import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from django.urls import reverse

import config

logger = logging.getLogger(__name__)


def _normalize_amount(amount) -> Decimal:
    if isinstance(amount, Decimal):
        return amount.quantize(Decimal('0.01'))
    if amount is None:
        return Decimal('0.00')
    try:
        return Decimal(str(amount)).quantize(Decimal('0.01'))
    except InvalidOperation:
        return Decimal('0.00')


def create_mercadopago_preference(request, description: str, amount, external_reference: str) -> dict | None:
    if not external_reference:
        return None
    normalized = _normalize_amount(amount)
    if normalized <= 0:
        return None
    base_url = config.MERCADOPAGO_BASE_URL.rstrip('/')
    url = f'{base_url}/checkout/preferences'
    payload = {
        'items': [
            {
                'title': description.strip() or 'Pagamento Aventureiros',
                'quantity': 1,
                'unit_price': float(normalized),
            }
        ],
        'external_reference': str(external_reference).strip(),
        'notification_url': request.build_absolute_uri(reverse('finance-mercadopago-webhook')),
        'auto_return': 'approved',
        'binary_mode': True,
        'back_urls': {
            'success': request.build_absolute_uri(reverse('dashboard')),
            'failure': request.build_absolute_uri(reverse('dashboard')),
            'pending': request.build_absolute_uri(reverse('dashboard')),
        },
    }
    payer_email = None
    if getattr(request, 'user', None):
        payer_email = getattr(request.user, 'email', None)
    if payer_email:
        payload['payer'] = {'email': payer_email.strip()}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {
        'Authorization': f'Bearer {config.MERCADOPAGO_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
    }
    request_obj = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            body = response.read()
            return json.loads(body or b'{}')
    except urllib.error.HTTPError as exc:
        logger.warning('Erro HTTP ao criar preferência MercadoPago %s: %s', external_reference, exc)
    except urllib.error.URLError as exc:
        logger.warning('Erro de rede ao criar preferência MercadoPago %s: %s', external_reference, exc)
    except json.JSONDecodeError:
        logger.exception('Resposta inválida ao criar preferência MercadoPago %s', external_reference)
    return None
