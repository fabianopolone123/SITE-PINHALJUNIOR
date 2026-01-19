from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from children.models import Child, GuardianChild
from core.permissions import role_required

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
            'description': 'Mensalidades em aberto do seu aventureiro',
            'action_url': request.path,
            'status_labels': STATUS_LABELS,
        },
    )
