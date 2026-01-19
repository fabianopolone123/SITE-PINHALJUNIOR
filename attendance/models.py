from django.conf import settings
from django.db import models

from children.models import Child


class AttendanceSession(models.Model):
    class Type(models.TextChoices):
        REUNIAO = 'REUNIAO', 'Reunião'
        EVENTO = 'EVENTO', 'Evento'
        AULA = 'AULA', 'Aula'

    date = models.DateField('Data')
    type = models.CharField('Tipo', max_length=20, choices=Type.choices)
    class_group = models.CharField('Turma/Unidade', max_length=80, blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sessions',
        verbose_name='Criado por',
    )

    class Meta:
        verbose_name = 'Sessão de Presença'
        verbose_name_plural = 'Sessões de Presença'
        ordering = ['-date', 'class_group']

    def __str__(self):
        return f'{self.get_type_display()} - {self.date} ({self.class_group})'


class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records', verbose_name='Sessão')
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='attendance_records', verbose_name='Aventureiro')
    present = models.BooleanField('Presente', default=False)
    note = models.TextField('Observação', blank=True)
    marked_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance',
        verbose_name='Marcado por',
    )
    marked_at = models.DateTimeField('Marcado em', auto_now_add=True)

    class Meta:
        unique_together = ('session', 'child')
        verbose_name = 'Registro de Presença'
        verbose_name_plural = 'Registros de Presença'
        ordering = ['child__name']

    def __str__(self):
        return f'{self.child} em {self.session}: {"Presente" if self.present else "Ausente"}'
