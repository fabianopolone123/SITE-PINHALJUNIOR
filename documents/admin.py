from django.contrib import admin

from .models import ChildDocument, DocumentFile, DocumentRequest, DocumentType


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'required', 'validity_days', 'active')
    list_filter = ('active', 'required')
    search_fields = ('name',)


@admin.register(ChildDocument)
class ChildDocumentAdmin(admin.ModelAdmin):
    list_display = ('child', 'document_type', 'status', 'received_date', 'valid_until', 'updated_by_user', 'updated_at')
    list_filter = ('status', 'document_type', 'child__class_group')
    search_fields = ('child__name', 'document_type__name', 'note')


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ('child_document', 'uploaded_by_user', 'uploaded_at')
    search_fields = ('child_document__child__name',)


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ('child', 'document_type', 'sent_to_user', 'sent_by_user', 'channel', 'status', 'sent_at')
    list_filter = ('channel', 'status', 'document_type')
    search_fields = ('child__name', 'sent_to_user__whatsapp_number')
