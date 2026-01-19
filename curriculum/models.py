from django.conf import settings
from django.db import models

from children.models import Child


class ContentItem(models.Model):
    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descrição', blank=True)
    order = models.IntegerField('Ordem', default=1)
    module = models.CharField('Módulo/Unidade', max_length=100, blank=True)
    active = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Conteúdo'
        verbose_name_plural = 'Conteúdos'

    def __str__(self):
        return f'{self.order}. {self.title}'


class ClassSchedule(models.Model):
    class Status(models.TextChoices):
        PLANEJADO = 'PLANEJADO', 'Planejado'
        DADO = 'DADO', 'Dado'

    class_group = models.CharField('Turma/Unidade', max_length=80)
    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE, related_name='schedules')
    planned_date = models.DateField('Data planejada')
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.PLANEJADO)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_schedules',
        verbose_name='Criado por',
    )

    class Meta:
        unique_together = ('class_group', 'content_item', 'planned_date')
        verbose_name = 'Cronograma de Conteúdo'
        verbose_name_plural = 'Cronogramas de Conteúdo'
        ordering = ['planned_date', 'class_group']

    def __str__(self):
        return f'{self.class_group} - {self.content_item} ({self.planned_date})'


class ChildProgress(models.Model):
    class Status(models.TextChoices):
        NAO_INICIADO = 'NAO_INICIADO', 'Não iniciado'
        EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
        CONCLUIDO = 'CONCLUIDO', 'Concluído'

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='curriculum_progress')
    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE, related_name='child_progress')
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.NAO_INICIADO)
    note = models.TextField('Observação', blank=True)
    marked_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_progress',
        verbose_name='Marcado por',
    )
    marked_at = models.DateTimeField('Marcado em', auto_now_add=True)

    class Meta:
        unique_together = ('child', 'content_item')
        verbose_name = 'Progresso do Aventureiro'
        verbose_name_plural = 'Progressos dos Aventureiros'
        ordering = ['-marked_at']

    def __str__(self):
        return f'{self.child} - {self.content_item}: {self.get_status_display()}'
