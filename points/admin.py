from django.contrib import admin

from .models import PointsLedger


@admin.register(PointsLedger)
class PointsLedgerAdmin(admin.ModelAdmin):
    list_display = ('child', 'points', 'created_by_user', 'created_at')
    list_filter = ('created_at', 'child', 'created_by_user')
    search_fields = ('child__name', 'reason', 'created_by_user__whatsapp_number')
