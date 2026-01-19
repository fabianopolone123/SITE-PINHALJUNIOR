from django.conf import settings
from django.db import models

from children.models import Child


class PointsLedger(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='points', verbose_name='Aventureiro')
    points = models.IntegerField('Pontos')
    reason = models.TextField('Motivo')
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points_created',
        verbose_name='Lançado por',
    )
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Lançamento de Pontos'
        verbose_name_plural = 'Lançamentos de Pontos'
        indexes = [
            models.Index(fields=['child', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.child} ({self.points} pts) - {self.reason[:30]}'
