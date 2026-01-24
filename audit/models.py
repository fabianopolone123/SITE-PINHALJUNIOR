from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activity_logs',
        verbose_name='Usuário',
    )
    method = models.CharField('Método HTTP', max_length=10)
    path = models.CharField('Caminho', max_length=500, db_index=True)
    view_name = models.CharField('Nome da view', max_length=200, blank=True)
    referer = models.CharField('Referer', max_length=500, blank=True)
    ip_address = models.CharField('Endereço IP', max_length=45, blank=True)
    user_agent = models.CharField('User-Agent', max_length=500, blank=True)
    status_code = models.PositiveIntegerField('Código de status', null=True, blank=True)
    success = models.BooleanField('Sucesso', default=True, db_index=True)
    duration_ms = models.FloatField('Duração (ms)', null=True, blank=True)
    message = models.TextField('Detalhes', blank=True)
    payload = models.JSONField('Dados enviados', blank=True, null=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Evento de Auditoria'
        verbose_name_plural = 'Eventos de Auditoria'

    def __str__(self):
        status = self.status_code or '??'
        return f'[{self.created_at:%Y-%m-%d %H:%M:%S}] {self.method} {self.path} ({status})'
