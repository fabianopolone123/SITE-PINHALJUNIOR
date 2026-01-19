from django.contrib import admin

from .models import Fee, Payment


@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('child', 'reference_month', 'amount', 'due_date', 'status', 'created_at')
    list_filter = ('status', 'reference_month', 'child__class_group')
    search_fields = ('child__name', 'reference_month')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('fee', 'amount', 'method', 'paid_at', 'created_at')
    list_filter = ('method',)
    search_fields = ('fee__child__name',)
