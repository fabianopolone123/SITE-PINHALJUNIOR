from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from children.models import Child, GuardianChild
from core.permissions import role_required

from .forms import PointsBatchForm, PointsIndividualForm, PointsExtractForm
from .models import PointsLedger

UserModel = get_user_model()

STAFF_ROLES = [
    User.Role.DIRETORIA,
    User.Role.SECRETARIA,
    User.Role.TESOUREIRO,
    User.Role.PROFESSOR,
    User.Role.ADM,
]


def _user_is_guardian_of(user, child: Child) -> bool:
    return GuardianChild.objects.filter(guardian_user=user, child=child).exists()


def _class_groups():
    return list(
        Child.objects.filter(active=True)
        .exclude(class_group='')
        .values_list('class_group', flat=True)
        .distinct()
        .order_by('class_group')
    )


@role_required(STAFF_ROLES)
def index(request):
    recent = PointsLedger.objects.select_related('child', 'created_by_user')[:20]
    return render(
        request,
        'points/index.html',
        {'recent': recent, 'title': 'Pontos'},
    )


@role_required(STAFF_ROLES)
def add_individual(request):
    form = PointsIndividualForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.created_by_user = request.user
        entry.save()
        messages.success(request, 'Lançamento registrado.')
        return redirect('points-child', child_id=entry.child_id)
    return render(request, 'points/add_individual.html', {'form': form, 'title': 'Lançar pontos (individual)'})


@role_required(STAFF_ROLES)
def add_batch(request):
    class_groups = _class_groups()
    form = PointsBatchForm(request.POST or None, class_groups=class_groups)
    children = []
    selected_class = None

    if request.method == 'POST' and form.is_valid():
        selected_class = form.cleaned_data['class_group']
        qs = Child.objects.filter(active=True)
        if selected_class:
            qs = qs.filter(class_group=selected_class)
        children = list(qs.order_by('name'))
        selected_ids = request.POST.getlist('children')
        if not selected_ids:
            messages.error(request, 'Selecione pelo menos um aventureiro.')
        else:
            with transaction.atomic():
                for cid in selected_ids:
                    child = next((c for c in children if str(c.id) == cid), None)
                    if not child:
                        continue
                    PointsLedger.objects.create(
                        child=child,
                        points=form.cleaned_data['points'],
                        reason=form.cleaned_data['reason'],
                        created_by_user=request.user,
                    )
            messages.success(request, f'Lançamentos criados para {len(selected_ids)} aventureiro(s).')
            return redirect('points-index')
    else:
        selected_class = ''
        children = list(Child.objects.filter(active=True).order_by('name'))

    return render(
        request,
        'points/add_batch.html',
        {
            'form': form,
            'children': children,
            'selected_class': selected_class,
            'title': 'Lançar pontos em lote',
        },
    )


def _child_accessible(request_user, child):
    if getattr(request_user, 'role', None) == User.Role.RESPONSAVEL:
        return _user_is_guardian_of(request_user, child)
    return getattr(request_user, 'role', None) in STAFF_ROLES


@role_required(STAFF_ROLES + [User.Role.RESPONSAVEL])
def child_statement(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    ledger = PointsLedger.objects.filter(child=child).order_by('-created_at')
    total = sum(item.points for item in ledger)
    return render(
        request,
        'points/child_statement.html',
        {'child': child, 'ledger': ledger, 'total': total, 'title': f'Extrato de {child.name}'},
    )


@role_required([User.Role.RESPONSAVEL])
def my_points(request):
    guardian_links = GuardianChild.objects.filter(guardian_user=request.user).select_related('child')
    children = [link.child for link in guardian_links]
    records = (
        PointsLedger.objects.filter(child__in=children)
        .select_related('child')
        .order_by('-created_at')
    )
    return render(
        request,
        'points/my_points.html',
        {'records': records, 'title': 'Pontos dos meus aventureiros'},
    )


@role_required(STAFF_ROLES + [User.Role.RESPONSAVEL])
def extract(request):
    child = None
    ledger = []
    total = 0
    form = PointsExtractForm(request.GET or None)
    if form.is_valid() and form.cleaned_data.get('child'):
        child = form.cleaned_data['child']
        if not _child_accessible(request.user, child):
            return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
        ledger = PointsLedger.objects.filter(child=child).order_by('-created_at')
        total = sum(item.points for item in ledger)
    return render(
        request,
        'points/extract.html',
        {'form': form, 'child': child, 'ledger': ledger, 'total': total, 'title': 'Extrato de pontos'},
    )
