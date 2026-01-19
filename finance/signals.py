import calendar
from datetime import date
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from children.models import Child
from .models import Fee

DEFAULT_FEE_AMOUNT = Decimal('30.00')
DEFAULT_DUE_DAY = 10


def compute_fee_amount(child: Child, base_amount: Decimal):
    discount_percent = getattr(child, 'fee_discount_percent', 0) or 0
    discount_amount = getattr(child, 'fee_discount_amount', 0) or 0
    if discount_percent:
        discount_amount += (base_amount * Decimal(discount_percent)) / Decimal(100)
    final = base_amount - discount_amount
    if final < 0:
        final = Decimal('0.00')
    return discount_amount, final


def generate_fees_for_child(child: Child):
    today = date.today()
    year = today.year
    for month in range(today.month, 13):
        ref = f'{year}-{month:02d}'
        try:
            last_day = calendar.monthrange(year, month)[1]
            due_day = min(DEFAULT_DUE_DAY, last_day)
            due = date(year, month, due_day)
        except Exception:
            due = today
        base_amount = DEFAULT_FEE_AMOUNT
        discount_amount, final_amount = compute_fee_amount(child, base_amount)
        Fee.objects.get_or_create(
            child=child,
            reference_month=ref,
            defaults={
                'amount': base_amount,
                'discount_amount': discount_amount,
                'final_amount': final_amount,
                'due_date': due,
                'status': Fee.Status.PENDENTE,
            },
        )


@receiver(post_save, sender=Child)
def create_fees_on_child_creation(sender, instance: Child, created, **kwargs):
    if created and instance.active:
        generate_fees_for_child(instance)
