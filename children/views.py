from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from core.permissions import role_required
from core.utils import redirect_for_role

from .forms import ChildForm, GuardianChildForm
from .models import Child, GuardianChild
from .utils import collect_children_payload, create_child_with_health

UserModel = get_user_model()

STAFF_ROLES = [
    User.Role.DIRETORIA,
    User.Role.SECRETARIA,
    User.Role.PROFESSOR,
    User.Role.TESOUREIRO,
]


def _is_staff_role(user):
    return getattr(user, 'role', None) in STAFF_ROLES


@role_required(STAFF_ROLES)
def child_list(request):
    children = Child.objects.all().order_by('name')
    return render(request, 'children/list.html', {'children': children, 'title': 'Aventureiros'})


@role_required([User.Role.DIRETORIA, User.Role.SECRETARIA])
def child_create(request):
    form = ChildForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Aventureiro cadastrado com sucesso.')
        return redirect('children-list')
    return render(request, 'children/form.html', {'form': form, 'title': 'Novo Aventureiro'})


@role_required([User.Role.DIRETORIA, User.Role.SECRETARIA])
def child_edit(request, pk):
    child = get_object_or_404(Child, pk=pk)
    form = ChildForm(request.POST or None, instance=child)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Dados atualizados.')
        return redirect('children-list')
    return render(request, 'children/form.html', {'form': form, 'title': f'Editar {child.name}'})


@role_required([User.Role.DIRETORIA, User.Role.SECRETARIA])
def vinculos_list(request):
    form = GuardianChildForm(request.POST or None)
    guardian_links = GuardianChild.objects.select_related('guardian_user', 'child').all()

    child_query = request.GET.get('child', '').strip()
    guardian_query = request.GET.get('guardian', '').strip()
    relationship_query = request.GET.get('relationship', '').strip()

    if child_query:
        guardian_links = guardian_links.filter(child__name__icontains=child_query)
    if guardian_query:
        guardian_links = guardian_links.filter(
            models.Q(guardian_user__first_name__icontains=guardian_query)
            | models.Q(guardian_user__last_name__icontains=guardian_query)
            | models.Q(guardian_user__whatsapp_number__icontains=guardian_query)
        )
    if relationship_query:
        guardian_links = guardian_links.filter(relationship__iexact=relationship_query)

    guardian_links = guardian_links.order_by('child__name', 'guardian_user__first_name')

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Vínculo registrado com sucesso.')
        return redirect('children-vinculos')

    return render(
        request,
        'children/vinculos.html',
        {
            'form': form,
            'guardian_links': guardian_links,
            'child_query': child_query,
            'guardian_query': guardian_query,
            'relationship_query': relationship_query,
            'title': 'Vínculos de Responsáveis',
        },
    )


@role_required([User.Role.RESPONSAVEL])
def meus_aventureiros(request):
    guardian_links = GuardianChild.objects.select_related('child').filter(guardian_user=request.user)
    children = [link.child for link in guardian_links]
    return render(
        request,
        'children/meus_aventureiros.html',
        {'children': children, 'title': 'Meus Aventureiros'},
    )


@role_required([User.Role.RESPONSAVEL])
def add_aventureiro(request):
    if request.method == 'POST':
        children_payload, errors = collect_children_payload(request.POST, request.FILES)
        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            for payload in children_payload:
                create_child_with_health(request.user, payload)
            messages.success(request, 'Aventureiro cadastrado com sucesso.')
            return redirect('children-meus')
    return render(request, 'children/add_for_responsavel.html', {'title': 'Adicionar aventureiro'})
