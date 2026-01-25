import json
import logging
import urllib.error
import urllib.request
import hashlib
import hmac
from datetime import datetime
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


def _build_notification_url(request):
    return request.build_absolute_uri(reverse('finance-mercadopago-webhook'))


def verify_mercadopago_signature(request) -> bool:
    secret = config.MERCADOPAGO_WEBHOOK_SECRET or ''
    if not secret:
        logger.warning('Segredo do webhook do MercadoPago não configurado, rejeitando chamada')
        return False
    header = (
        request.META.get('HTTP_X_HUB_SIGNATURE')
        or request.META.get('HTTP_X_MERCADOPAGO_SIGNATURE')
        or ''
    )
    if not header:
        logger.warning('Assinatura do MercadoPago ausente no webhook')
        return False
    algo = 'sha1'
    signature = header
    if '=' in header:
        algo_name, signature = header.split('=', 1)
        algo = algo_name.lower()
    try:
        digestmod = getattr(hashlib, algo)
    except AttributeError:
        logger.warning('Algoritmo de assinatura desconhecido: %s', algo)
        return False
    computed = hmac.new(secret.encode('utf-8'), request.body or b'', digestmod).hexdigest()
    valid = hmac.compare_digest(computed, signature)
    if not valid:
        logger.warning('Assinatura do MercadoPago inválida: %s', signature)
    return valid


def create_mercadopago_pix_payment(request, description: str, amount, external_reference: str) -> dict | None:
    if not external_reference:
        return None
    normalized = _normalize_amount(amount)
    if normalized <= 0:
        return None
    base_url = config.MERCADOPAGO_BASE_URL.rstrip('/')
    url = f'{base_url}/v1/payments'
    payload = {
        'transaction_amount': float(normalized),
        'currency_id': 'BRL',
        'payment_method_id': 'pix',
        'description': description.strip() or 'Pagamento Aventureiros',
        'external_reference': str(external_reference).strip(),
        'notification_url': _build_notification_url(request),
        'binary_mode': True,
        'date_of_expiration': (datetime.utcnow().isoformat() + 'Z'),
    }
    payer_email = ''
    payer = {}
    if getattr(request, 'user', None):
        payer_email = getattr(request.user, 'email', '') or ''
    if payer_email:
        payer['email'] = payer_email.strip()
    if payer:
        payload['payer'] = payer
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {
        'Authorization': f'Bearer {config.MERCADOPAGO_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
    }
    request_obj = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            body = response.read()
            data = json.loads(body or b'{}')
            interaction = data.get('point_of_interaction', {}).get('data', {})
            return {
                'id': data.get('id'),
                'status': data.get('status'),
                'transaction_amount': data.get('transaction_amount'),
                'expiration_date': interaction.get('date_of_expiration'),
                'qr_code': interaction.get('qr_code'),
                'qr_code_base64': interaction.get('qr_code_base64'),
                'external_reference': data.get('external_reference'),
            }
    except urllib.error.HTTPError as exc:
        logger.warning('Erro HTTP ao criar pagamento PIX MercadoPago %s: %s', external_reference, exc)
    except urllib.error.URLError as exc:
        logger.warning('Erro de rede ao criar pagamento PIX MercadoPago %s: %s', external_reference, exc)
    except json.JSONDecodeError:
        logger.exception('Resposta invalida ao criar pagamento PIX MercadoPago %s', external_reference)
    return None
