from datetime import date, timedelta

from django.conf import settings
from django.db import models

from children.models import Child


class DocumentType(models.Model):
    name = models.CharField('Nome', max_length=120)
    required = models.BooleanField('Obrigatório', default=True)
    validity_days = models.IntegerField('Validade (dias)', null=True, blank=True)
    active = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documento'
        ordering = ['name']

    def __str__(self):
        return self.name


class ChildDocument(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        RECEBIDO = 'RECEBIDO', 'Recebido'
        VENCIDO = 'VENCIDO', 'Vencido'
        REJEITADO = 'REJEITADO', 'Rejeitado'

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='documents', verbose_name='Aventureiro')
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='child_documents')
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.PENDENTE)
    received_date = models.DateField('Recebido em', null=True, blank=True)
    valid_until = models.DateField('Válido até', null=True, blank=True)
    note = models.TextField('Observação', blank=True)
    updated_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_documents',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('child', 'document_type')
        verbose_name = 'Documento da Criança'
        verbose_name_plural = 'Documentos das Crianças'

    def __str__(self):
        return f'{self.child} - {self.document_type} ({self.status})'

    def apply_validity(self):
        if self.document_type.validity_days and self.received_date:
            self.valid_until = self.received_date + timedelta(days=self.document_type.validity_days)
            if self.valid_until < date.today():
                self.status = self.Status.VENCIDO
        else:
            self.valid_until = None


class DocumentFile(models.Model):
    child_document = models.ForeignKey(ChildDocument, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='documents/')
    uploaded_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Arquivo de Documento'
        verbose_name_plural = 'Arquivos de Documento'

    def __str__(self):
        return f'{self.child_document} - arquivo'


class DocumentRequest(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        SITE = 'SITE', 'Site'

    class Status(models.TextChoices):
        ENVIADO = 'ENVIADO', 'Enviado'
        RESPONDIDO = 'RESPONDIDO', 'Respondido'
        RESOLVIDO = 'RESOLVIDO', 'Resolvido'

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='document_requests')
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='requests')
    sent_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_requests_received',
    )
    sent_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_requests_sent',
    )
    channel = models.CharField('Canal', max_length=20, choices=Channel.choices, default=Channel.WHATSAPP)
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.ENVIADO)
    message = models.TextField('Mensagem')
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Solicitação de Documento'
        verbose_name_plural = 'Solicitações de Documento'
        ordering = ['-sent_at']

    def __str__(self):
        return f'{self.child} - {self.document_type} ({self.status})'
