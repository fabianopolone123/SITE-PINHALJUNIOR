import csv
import json
from datetime import timedelta

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

from .models import ActivityLog


class RecentMinutesFilter(admin.SimpleListFilter):
    title = 'Intervalo recente'
    parameter_name = 'recent_minutes'

    def lookups(self, request, model_admin):
        return (
            ('15', 'Últimos 15 minutos'),
            ('60', 'Última hora'),
            ('180', 'Últimas 3 horas'),
            ('1440', 'Último dia'),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        cutoff = timezone.now() - timedelta(minutes=int(self.value()))
        return queryset.filter(created_at__gte=cutoff)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'method', 'path', 'status_code', 'success', 'duration_ms')
    list_filter = ('method', 'status_code', 'success', 'user', RecentMinutesFilter, 'created_at')
    search_fields = ('path', 'message', 'view_name', 'referer')
    date_hierarchy = 'created_at'
    list_select_related = ('user',)
    readonly_fields = (
        'created_at',
        'user',
        'method',
        'path',
        'view_name',
        'referer',
        'ip_address',
        'user_agent',
        'status_code',
        'success',
        'duration_ms',
        'message',
        'payload',
    )
    change_list_template = 'admin/audit/activitylog/change_list.html'
    actions = ['export_selected_as_csv']
    max_export_rows = 10000

    def changelist_view(self, request, extra_context=None):
        if request.GET.get('export') == 'csv':
            queryset = self.get_queryset(request)
            return self._export_csv_response(queryset, filename='activity-logs')
        extra_context = extra_context or {}
        query_params = request.GET.copy()
        query_params.pop('export', None)
        extra_context['export_query'] = query_params.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description='Exportar registros selecionados (CSV)')
    def export_selected_as_csv(self, request, queryset):
        return self._export_csv_response(queryset, filename='activity-logs-selected')

    def _export_csv_response(self, queryset, filename):
        limit = self.max_export_rows
        queryset = queryset.order_by('-created_at')[:limit]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}.csv'
        writer = csv.writer(response)
        writer.writerow([
            'Criado em',
            'Usuário',
            'Método',
            'Caminho',
            'View',
            'Status',
            'Sucesso',
            'Duração (ms)',
            'IP',
            'Referer',
            'Mensagem',
            'Dados enviados',
        ])
        for log in queryset:
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                str(log.user or ''),
                log.method,
                log.path,
                log.view_name,
                log.status_code or '',
                'Sim' if log.success else 'Não',
                f'{log.duration_ms:.1f}' if log.duration_ms else '',
                log.ip_address,
                log.referer,
                log.message,
                self._stringify_payload(log.payload),
            ])
        return response

    def _stringify_payload(self, payload):
        if not payload:
            return ''
        try:
            return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        except Exception:
            return str(payload)
