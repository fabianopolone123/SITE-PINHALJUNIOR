import urllib.parse
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from children.models import Child, GuardianChild
from core.permissions import role_required

from .forms import ChildDocumentUpdateForm, DocumentUploadForm
from .models import ChildDocument, DocumentFile, DocumentRequest, DocumentType

UserModel = get_user_model()

SECRETARIA_ROLES = [User.Role.SECRETARIA, User.Role.DIRETORIA]
RESP_ROLES = [User.Role.RESPONSAVEL]


def _child_accessible(user, child):
    if getattr(user, 'role', None) in SECRETARIA_ROLES:
        return True
    if getattr(user, 'role', None) == User.Role.RESPONSAVEL:
        return GuardianChild.objects.filter(guardian_user=user, child=child).exists()
    return False


@role_required(SECRETARIA_ROLES)
def overview(request):
    docs = (
        ChildDocument.objects.select_related('child', 'document_type')
        .order_by('child__class_group', 'child__name', 'document_type__name')
    )
    return render(request, 'documents/overview.html', {'docs': docs, 'title': 'Documentação'})


@role_required(SECRETARIA_ROLES + RESP_ROLES)
def child_detail(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    docs = ChildDocument.objects.filter(child=child).select_related('document_type')
    requests = DocumentRequest.objects.filter(child=child).order_by('-sent_at')
    return render(
        request,
        'documents/child_detail.html',
        {'child': child, 'docs': docs, 'requests': requests, 'title': f'Documentos de {child.name}'},
    )


@role_required(SECRETARIA_ROLES)
def child_doc_update(request, child_id, doc_id):
    child = get_object_or_404(Child, pk=child_id)
    doc = get_object_or_404(ChildDocument, pk=doc_id, child=child)
    form = ChildDocumentUpdateForm(request.POST or None, instance=doc)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by_user = request.user
        if obj.status == ChildDocument.Status.RECEBIDO:
            obj.apply_validity()
        obj.save()
        messages.success(request, 'Status atualizado.')
        return redirect('documents-child', child_id=child.id)
    return render(request, 'documents/doc_update_form.html', {'form': form, 'child': child, 'doc': doc, 'title': 'Atualizar documento'})


@role_required(SECRETARIA_ROLES)
def child_doc_upload(request, child_id, doc_id):
    child = get_object_or_404(Child, pk=child_id)
    doc = get_object_or_404(ChildDocument, pk=doc_id, child=child)
    form = DocumentUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        upload = form.save(commit=False)
        upload.child_document = doc
        upload.uploaded_by_user = request.user
        upload.save()
        messages.success(request, 'Arquivo anexado.')
        return redirect('documents-child', child_id=child.id)
    return render(request, 'documents/doc_upload.html', {'form': form, 'child': child, 'doc': doc, 'title': 'Upload de documento'})


@role_required(SECRETARIA_ROLES)
def send_request(request, child_id, doctype_id):
    child = get_object_or_404(Child, pk=child_id)
    doc_type = get_object_or_404(DocumentType, pk=doctype_id)
    guardian_link = GuardianChild.objects.filter(child=child).select_related('guardian_user').first()
    if not guardian_link:
        messages.error(request, 'Nenhum responsável vinculado.')
        return redirect('documents-child', child_id=child.id)

    responsible = guardian_link.guardian_user
    msg = (
        f"Olá {responsible.full_name or responsible.whatsapp_number},\\n"
        f"Precisamos do documento '{doc_type.name}' de {child.name}.\\n"
        "Envie foto deste documento aqui no WhatsApp. Obrigado!"
    )
    encoded = urllib.parse.quote(msg)
    phone = responsible.whatsapp_number.lstrip('+')
    wa_url = f'https://wa.me/{phone}?text={encoded}'

    DocumentRequest.objects.get_or_create(
        child=child,
        document_type=doc_type,
        sent_to_user=responsible,
        sent_by_user=request.user,
        channel=DocumentRequest.Channel.WHATSAPP,
        message=msg,
        defaults={'status': DocumentRequest.Status.ENVIADO},
    )
    messages.success(request, 'Cobrança registrada. Abra o link do WhatsApp para enviar.')
    return redirect(wa_url)


@role_required(RESP_ROLES)
def my_documents(request):
    guardian_links = GuardianChild.objects.filter(guardian_user=request.user).select_related('child')
    children = [link.child for link in guardian_links]
    docs_map = {
        child.id: ChildDocument.objects.filter(child=child).select_related('document_type')
        for child in children
    }
    return render(
        request,
        'documents/my_documents.html',
        {'children': children, 'docs_map': docs_map, 'title': 'Documentos'},
    )
