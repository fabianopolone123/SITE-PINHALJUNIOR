import json
import logging
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import User
from children.models import Child, GuardianChild
from core.mercadopago import create_mercadopago_pix_payment
from core.permissions import role_required

import config

from .forms import FeeFilterForm, FeeGenerationForm
from .models import Fee, Payment
from .signals import compute_fee_amount

UserModel = get_user_model()

TESOUREIRO = [User.Role.TESOUREIRO]
RESP = [User.Role.RESPONSAVEL]
DIRETORIA = [User.Role.DIRETORIA]


def _child_accessible(user, child):
    if getattr(user, 'role', None) in TESOUREIRO + DIRETORIA:
        return True
    if getattr(user, 'role', None) == User.Role.RESPONSAVEL:
        return GuardianChild.objects.filter(guardian_user=user, child=child).exists()
    return False


def _effective_status(fee: Fee):
    if fee.status == Fee.Status.PENDENTE and fee.due_date < date.today():
        return Fee.Status.ATRASADO
    return fee.status


def _build_pix_code(prefix: str, identifier: str, amount: Decimal) -> str:
    cents = int((amount or Decimal('0.00')) * 100)
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'PIX-{prefix}-{identifier}-{timestamp}-{cents}'


def _is_open_fee(fee: Fee, current_ref: str) -> bool:
    effective = _effective_status(fee)
    return (
        fee.status != Fee.Status.PAGO
        and (effective == Fee.Status.PENDENTE or effective == Fee.Status.ATRASADO)
        and fee.reference_month <= current_ref
    )


STATUS_LABELS = {choice[0]: choice[1] for choice in Fee.Status.choices}

logger = logging.getLogger(__name__)


@role_required(TESOUREIRO + DIRETORIA)
def fees_list(request):
    form = FeeFilterForm(request.GET or None)
    qs = Fee.objects.select_related('child').all()
    if form.is_valid():
        ref = form.cleaned_data.get('reference_month')
        status = form.cleaned_data.get('status')
        class_group = form.cleaned_data.get('class_group')
        if ref:
            qs = qs.filter(reference_month=ref)
        if status:
            if status == Fee.Status.ATRASADO:
                today = date.today()
                qs = qs.filter(
                    Q(status=Fee.Status.ATRASADO)
                    | (Q(status=Fee.Status.PENDENTE) & Q(due_date__lt=today))
                )
            else:
                qs = qs.filter(status=status)
        if class_group:
            qs = qs.filter(child__class_group=class_group)
    fees = list(qs.order_by('child__name'))
    # annotate effective status
    for f in fees:
        f.effective_status = _effective_status(f)
    return render(request, 'finance/fees_list.html', {'fees': fees, 'form': form, 'title': 'Mensalidades'})


@role_required(TESOUREIRO)
def fee_generate(request):
    form = FeeGenerationForm(request.POST or None)
    created = 0
    if request.method == 'POST' and form.is_valid():
        ref = form.cleaned_data['reference_month']
        amount = form.cleaned_data['amount']
        due = form.cleaned_data['due_date']
        cg = form.cleaned_data.get('class_group')
        child = form.cleaned_data.get('child')
        children = []
        if cg:
            children = list(Child.objects.filter(class_group=cg, active=True))
        elif child:
            children = [child]
        with transaction.atomic():
            for kid in children:
                discount_amount, final_amount = compute_fee_amount(kid, amount)
                fee, created_flag = Fee.objects.get_or_create(
                    child=kid,
                    reference_month=ref,
                    defaults={
                        'amount': amount,
                        'discount_amount': discount_amount,
                        'final_amount': final_amount,
                        'due_date': due,
                        'status': Fee.Status.PENDENTE,
                    },
                )
                if created_flag:
                    created += 1
        messages.success(request, f'{created} mensalidade(s) gerada(s).')
        return redirect('finance-fees')
    return render(request, 'finance/fee_form.html', {'form': form, 'title': 'Gerar mensalidades'})


@role_required(TESOUREIRO + DIRETORIA + RESP)
def child_fees(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    fees = list(Fee.objects.filter(child=child).order_by('-reference_month'))
    for f in fees:
        f.effective_status = _effective_status(f)
    return render(request, 'finance/child_fees.html', {'child': child, 'fees': fees, 'title': f'Mensalidades de {child.name}'})


@role_required(TESOUREIRO + DIRETORIA)
def reports(request):
    fees = Fee.objects.all()
    total = fees.count()
    pagos = fees.filter(status=Fee.Status.PAGO).count()
    pendentes = fees.filter(status=Fee.Status.PENDENTE).count()
    atrasados = sum(1 for f in fees if _effective_status(f) == Fee.Status.ATRASADO)
    return render(
        request,
        'finance/reports.html',
        {'total': total, 'pagos': pagos, 'pendentes': pendentes, 'atrasados': atrasados, 'title': 'Relatórios'},
    )


@role_required(RESP)
def my_fees(request):
    guardian_links = GuardianChild.objects.filter(guardian_user=request.user).select_related('child')
    children = [link.child for link in guardian_links]
    current_ref = date.today().strftime('%Y-%m')
    child_finances = []
    for child in children:
        fees = list(Fee.objects.filter(child=child).order_by('-reference_month'))
        entries = []
        open_entries = []
        open_total = Decimal('0.00')
        for fee in fees:
            effective = _effective_status(fee)
            entry = {
                'fee': fee,
                'effective_status': effective,
                'is_open': _is_open_fee(fee, current_ref),
            }
            entries.append(entry)
            if _is_open_fee(fee, current_ref):
                open_entries.append(entry)
                open_total += fee.final_amount or Decimal('0.00')
        child_finances.append(
            {
                'child': child,
                'entries': entries,
                'open_total': open_total,
                'open_entries': open_entries,
            }
        )
    return render(
        request,
        'finance/my_fees.html',
        {
            'child_finances': child_finances,
            'title': 'Financeiro',
            'status_labels': STATUS_LABELS,
        },
    )


@role_required(RESP)
def my_child_fees(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    fees = list(Fee.objects.filter(child=child).order_by('-reference_month'))
    for f in fees:
        f.effective_status = _effective_status(f)
    return render(request, 'finance/child_fees.html', {'child': child, 'fees': fees, 'title': f'Mensalidades de {child.name}'})


@role_required(RESP)
def fee_payment(request, child_id, fee_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    fee = get_object_or_404(Fee, pk=fee_id, child=child)
    effective = _effective_status(fee)
    pix_code = _build_pix_code('FEE', str(fee.id), fee.final_amount or Decimal('0.00'))
    mp_payment = create_mercadopago_pix_payment(
        request,
        description=f'Mensalidade {fee.reference_month} - {child.name}',
        amount=fee.final_amount or Decimal('0.00'),
        external_reference=f'FEE:{fee.id}',
    )
    mp_payment_error = None
    if not mp_payment:
        mp_payment_error = 'Não foi possível gerar o QR oficial do MercadoPago. Confira os logs para ver o erro retornado pela API.'
        logger.error('Falha ao criar pagamento Pix MercadoPago para Fee %s (user %s)', fee_id, request.user.whatsapp_number)
    if request.method == 'POST':
        Payment.objects.create(
            fee=fee,
            amount=fee.final_amount or Decimal('0.00'),
            method='PIX',
            paid_at=timezone.now(),
        )
        fee.status = Fee.Status.PAGO
        fee.save()
        messages.success(request, 'Pagamento da mensalidade registrado. Obrigado!')
        return redirect('finance-my-child', child_id=child.id)
    return render(
        request,
        'finance/pix_payment.html',
        {
            'child': child,
            'title': f'Pagamento {fee.reference_month}',
            'fees': [{'fee': fee, 'effective_status': effective}],
            'total_amount': fee.final_amount or Decimal('0.00'),
            'pix_code': pix_code,
            'mp_payment': mp_payment,
            'mp_payment_error': mp_payment_error,
            'description': f'Mensalidade {fee.reference_month}',
            'action_url': request.path,
            'status_labels': STATUS_LABELS,
        },
    )


@role_required(RESP)
def pay_all_open(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    current_ref = date.today().strftime('%Y-%m')
    fees = list(Fee.objects.filter(child=child).order_by('-reference_month'))
    open_entries = []
    total = Decimal('0.00')
    for fee in fees:
        effective = _effective_status(fee)
        entry = {'fee': fee, 'effective_status': effective}
        if _is_open_fee(fee, current_ref):
            open_entries.append(entry)
            total += fee.final_amount or Decimal('0.00')
    if not open_entries:
        messages.info(request, 'Não há mensalidades em aberto para pagar no momento.')
        return redirect('finance-my-child', child_id=child.id)
    pix_code = _build_pix_code('ALL', f'{child.id}', total or Decimal('0.00'))
    mp_payment = create_mercadopago_pix_payment(
        request,
        description=f'Mensalidades em aberto de {child.name}',
        amount=total,
        external_reference=f'FEE_OPEN:{child.id}',
    )
    mp_payment_error = None
    if not mp_payment:
        mp_payment_error = 'Não foi possível gerar o QR oficial do MercadoPago. Confira os logs para ver o erro retornado pela API.'
        logger.error('Falha ao criar pagamento Pix MercadoPago para fee aberto do child %s (user %s)', child_id, request.user.whatsapp_number)
    if request.method == 'POST':
        with transaction.atomic():
            for entry in open_entries:
                fee = entry['fee']
                Payment.objects.create(
                    fee=fee,
                    amount=fee.final_amount or Decimal('0.00'),
                    method='PIX',
                    paid_at=timezone.now(),
                )
                fee.status = Fee.Status.PAGO
                fee.save()
        messages.success(request, 'Pagamentos das mensalidades em aberto confirmados.')
        return redirect('finance-my-child', child_id=child.id)
    return render(
        request,
        'finance/pix_payment.html',
        {
            'child': child,
            'title': 'Pagamento de mensalidades em aberto',
            'fees': open_entries,
            'total_amount': total,
            'pix_code': pix_code,
            'mp_payment': mp_payment,
            'description': 'Mensalidades em aberto do seu aventureiro',
            'action_url': request.path,
            'status_labels': STATUS_LABELS,
            'mp_payment_error': mp_payment_error,
        },
    )


def _extract_payment_amount(payment_data):
    if not payment_data:
        return None
    for key in ('transaction_amount',):
        value = payment_data.get(key)
        if value is not None:
            try:
                return Decimal(str(value))
            except (TypeError, InvalidOperation):
                break
    details = payment_data.get('transaction_details') or {}
    net_amount = details.get('net_received_amount')
    if net_amount is not None:
        try:
            return Decimal(str(net_amount))
        except (TypeError, InvalidOperation):
            pass
    return None


def _parse_payment_timestamp(value):
    if not value:
        return None
    normalized = value.upper().replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = timezone.make_aware(parsed)
    return parsed


def _build_payment_note(payment_data):
    payer = payment_data.get('payer') or {}
    if not isinstance(payer, dict):
        return 'Pagamento MercadoPago'
    parts = []
    first_name = payer.get('first_name')
    last_name = payer.get('last_name')
    full_name = ' '.join(filter(None, (first_name or '', last_name or ''))).strip()
    if full_name:
        parts.append(full_name)
    email = payer.get('email')
    if email:
        parts.append(email)
    identification = payer.get('identification') or {}
    id_number = identification.get('number')
    if id_number:
        id_label = identification.get('type', 'ID')
        parts.append(f'{id_label}:{id_number}')
    return ' '.join(parts) or 'Pagamento MercadoPago'


def _mark_fee_paid(payment_id, fee_id, payment_data):
    fee = Fee.objects.filter(pk=fee_id).first()
    if not fee:
        logger.warning('Fee %s não encontrada para pagamento %s', fee_id, payment_id)
        return False
    if Payment.objects.filter(external_id=str(payment_id)).exists():
        logger.info('Pagamento %s já processado para mensalidade %s', payment_id, fee_id)
        return True
    amount = _extract_payment_amount(payment_data)
    if amount is None:
        amount = fee.final_amount or Decimal('0.00')
    payment_method = payment_data.get('payment_method_id') or payment_data.get('payment_type') or ''
    paid_at = _parse_payment_timestamp(payment_data.get('date_approved')) or timezone.now()
    note = _build_payment_note(payment_data)
    with transaction.atomic():
        Payment.objects.create(
            fee=fee,
            amount=amount,
            method=payment_method,
            paid_at=paid_at,
            note=note,
            external_id=str(payment_id),
            external_reference=payment_data.get('external_reference') or '',
        )
        if fee.status != Fee.Status.PAGO:
            fee.status = Fee.Status.PAGO
            fee.save(update_fields=['status'])
    logger.info('Mensalidade %s marcada como paga pelo MercadoPago (%s)', fee_id, payment_id)
    return True


def _mark_order_paid(payment_id, order_id, payment_data):
    try:
        from store.models import Order
    except ImportError:
        logger.error('Não foi possível importar store.models para processar pedido %s', order_id)
        return False
    order = Order.objects.filter(pk=order_id).first()
    if not order:
        logger.warning('Pedido %s não encontrado para pagamento %s', order_id, payment_id)
        return False
    if order.status == Order.Status.PAID:
        logger.info('Pedido %s já estava pago quando o MercadoPago notificou %s', order_id, payment_id)
        return True
    amount = _extract_payment_amount(payment_data)
    if amount is not None and order.total and amount != order.total:
        logger.warning(
            'Pedido %s tem total %s mas pagamento %s chegou com %s',
            order_id,
            order.total,
            payment_id,
            amount,
        )
    order.status = Order.Status.PAID
    order.save(update_fields=['status'])
    logger.info('Pedido %s marcado como pago pelo MercadoPago (%s)', order_id, payment_id)
    return True


def _mark_child_open_fees_paid(payment_id, child_id, payment_data):
    child = Child.objects.filter(pk=child_id).first()
    if not child:
        logger.warning('Responsável %s não encontrado para pagamento %s', child_id, payment_id)
        return False
    current_ref = date.today().strftime('%Y-%m')
    open_fees = [fee for fee in Fee.objects.filter(child=child) if _is_open_fee(fee, current_ref)]
    if not open_fees:
        logger.info('Nenhuma mensalidade em aberto encontrada para %s durante o pagamento %s', child_id, payment_id)
        return False
    payment_method = payment_data.get('payment_method_id') or payment_data.get('payment_type') or ''
    paid_at = _parse_payment_timestamp(payment_data.get('date_approved')) or timezone.now()
    note = _build_payment_note(payment_data)
    created = 0
    with transaction.atomic():
        for fee in open_fees:
            if Payment.objects.filter(external_id=str(payment_id), fee=fee).exists():
                continue
            Payment.objects.create(
                fee=fee,
                amount=fee.final_amount or Decimal('0.00'),
                method=payment_method,
                paid_at=paid_at,
                note=note,
                external_id=str(payment_id),
                external_reference=payment_data.get('external_reference') or '',
            )
            if fee.status != Fee.Status.PAGO:
                fee.status = Fee.Status.PAGO
                fee.save(update_fields=['status'])
            created += 1
    logger.info('Mensalidades em aberto de %s marcadas como pagas via MercadoPago (%s): %s entradas', child_id, payment_id, created)
    return created > 0


def _process_mercadopago_payment(payment_id, payment_data):
    reference = (payment_data.get('external_reference') or '').strip()
    if not reference or ':' not in reference:
        logger.warning('Pagamento %s sem referência válida: %s', payment_id, reference)
        return False
    prefix, identifier = reference.split(':', 1)
    prefix = prefix.upper()
    identifier = identifier.strip()
    if not identifier.isdigit():
        logger.warning('Referência %s em pagamento %s não contém identificador numérico', reference, payment_id)
        return False
    if prefix == 'FEE':
        return _mark_fee_paid(payment_id, identifier, payment_data)
    if prefix in {'FEE_ALL', 'FEEALL', 'FEE_OPEN'}:
        return _mark_child_open_fees_paid(payment_id, identifier, payment_data)
    if prefix == 'ORDER':
        return _mark_order_paid(payment_id, identifier, payment_data)
    logger.warning('Prefixo de referência desconhecido %s para pagamento %s', prefix, payment_id)
    return False


def _fetch_mercadopago_payment(payment_id):
    base_url = config.MERCADOPAGO_BASE_URL.rstrip('/')
    url = f'{base_url}/v1/payments/{payment_id}'
    headers = {'Authorization': f'Bearer {config.MERCADOPAGO_ACCESS_TOKEN}'}
    request_obj = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        logger.warning('Erro HTTP ao buscar pagamento %s: %s', payment_id, exc)
    except urllib.error.URLError as exc:
        logger.warning('Erro de rede ao buscar pagamento %s: %s', payment_id, exc)
    return None


@csrf_exempt
def mercadopago_webhook(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    data = payload.get('data') or {}
    payment_id = data.get('id') or payload.get('id') or request.GET.get('id')
    if not payment_id:
        return HttpResponseBadRequest('Falta o ID do pagamento')
    payment_data = _fetch_mercadopago_payment(payment_id)
    if not payment_data:
        return HttpResponse(status=204)
    if payment_data.get('status') != 'approved':
        return HttpResponse(status=204)
    processed = _process_mercadopago_payment(payment_id, payment_data)
    logger.info('Webhook MercadoPago %s processado=%s', payment_id, processed)
    if processed:
        return JsonResponse({'status': 'ok'})
    return HttpResponse(status=204)
