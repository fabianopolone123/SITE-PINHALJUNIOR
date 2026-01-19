from decimal import Decimal
from django.conf import settings
from django.db import models

from children.models import Child


class Fee(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        PAGO = 'PAGO', 'Pago'
        ATRASADO = 'ATRASADO', 'Atrasado'
        ISENTO = 'ISENTO', 'Isento'
        EM_NEGOCIACAO = 'EM_NEGOCIACAO', 'Em negociação'

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='fees')
    reference_month = models.CharField('Mês de referência (YYYY-MM)', max_length=7)
    amount = models.DecimalField('Valor base', max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField('Desconto', max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_amount = models.DecimalField('Valor final', max_digits=10, decimal_places=2, default=Decimal('0.00'))
    due_date = models.DateField('Vencimento')
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.PENDENTE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('child', 'reference_month')
        ordering = ['-reference_month', 'child__name']
        verbose_name = 'Mensalidade'
        verbose_name_plural = 'Mensalidades'

    def __str__(self):
        return f'{self.child} {self.reference_month} ({self.final_amount})'

    def save(self, *args, **kwargs):
        # recalcula desconto/final com base no desconto do responsável/criança
        if self.child_id:
            extra_discount = Decimal(getattr(self.child, 'fee_discount_amount', 0) or 0)
            percent = Decimal(getattr(self.child, 'fee_discount_percent', 0) or 0)
            total_discount = (self.amount * percent / Decimal('100')) + extra_discount + self.discount_amount
            if total_discount < 0:
                total_discount = Decimal('0.00')
            final = self.amount - total_discount
            if final < 0:
                final = Decimal('0.00')
            self.discount_amount = total_discount
            self.final_amount = final
        super().save(*args, **kwargs)


class Payment(models.Model):
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField('Valor pago', max_digits=10, decimal_places=2)
    method = models.CharField('Método', max_length=50, blank=True)
    paid_at = models.DateTimeField('Pago em', null=True, blank=True)
    note = models.TextField('Observação', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'

    def __str__(self):
        return f'Pgto {self.amount} para {self.fee}'
