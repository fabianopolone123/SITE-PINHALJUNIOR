from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from children.models import Child
from core.permissions import role_required

from .models import Fee

OPEN_STATUSES = [Fee.Status.PENDENTE, Fee.Status.ATRASADO, Fee.Status.EM_NEGOCIACAO]


@role_required([User.Role.TESOUREIRO])
def apply_discount(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    open_fees = Fee.objects.filter(child=child, status__in=OPEN_STATUSES).order_by('-reference_month')

    if request.method == 'POST':
        percent = request.POST.get('percent') or '0'
        amount = request.POST.get('amount') or '0'
        fee_id = request.POST.get('fee_id') or ''
        try:
            percent_val = Decimal(percent)
        except Exception:
            percent_val = Decimal('0')
        try:
            amount_val = Decimal(amount)
        except Exception:
            amount_val = Decimal('0')

        if fee_id:
            target_fees = open_fees.filter(id=fee_id)
        else:
            target_fees = open_fees

        for fee in target_fees:
            total_discount = (fee.amount * percent_val / Decimal('100')) + amount_val
            if total_discount < 0:
                total_discount = Decimal('0.00')
            final = fee.amount - total_discount
            if final < 0:
                final = Decimal('0.00')
            fee.discount_amount = total_discount
            fee.final_amount = final
            fee.save()

        messages.success(request, 'Desconto aplicado nas mensalidades selecionadas.')
        return redirect('finance-child-fees', child_id=child.id)

    return render(
        request,
        'finance/discount_form.html',
        {'child': child, 'open_fees': open_fees, 'title': 'Aplicar desconto'},
    )
