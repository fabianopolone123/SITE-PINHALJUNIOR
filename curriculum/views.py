from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from children.models import Child, GuardianChild
from core.permissions import role_required

from .forms import ClassScheduleForm, ContentItemForm, ProgressSelectionForm
from .models import ChildProgress, ClassSchedule, ContentItem

UserModel = get_user_model()

STAFF_VIEW_ROLES = [User.Role.DIRETORIA, User.Role.PROFESSOR]
PROGRESS_MARK_ROLE = [User.Role.PROFESSOR]
RESP_ROLE = [User.Role.RESPONSAVEL]


def _class_groups():
    return (
        Child.objects.filter(active=True)
        .exclude(class_group='')
        .values_list('class_group', flat=True)
        .distinct()
        .order_by('class_group')
    )


def _child_accessible(request_user, child):
    if getattr(request_user, 'role', None) == User.Role.RESPONSAVEL:
        return GuardianChild.objects.filter(guardian_user=request_user, child=child).exists()
    return getattr(request_user, 'role', None) in STAFF_VIEW_ROLES + PROGRESS_MARK_ROLE


@role_required(STAFF_VIEW_ROLES)
def content_list(request):
    items = ContentItem.objects.all()
    return render(request, 'curriculum/content_list.html', {'items': items, 'title': 'Conteúdos'})


@role_required(STAFF_VIEW_ROLES)
def content_create(request):
    form = ContentItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Conteúdo criado.')
        return redirect('curriculum-content')
    return render(request, 'curriculum/content_form.html', {'form': form, 'title': 'Novo conteúdo'})


@role_required(STAFF_VIEW_ROLES)
def content_edit(request, pk):
    item = get_object_or_404(ContentItem, pk=pk)
    form = ContentItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Conteúdo atualizado.')
        return redirect('curriculum-content')
    return render(request, 'curriculum/content_form.html', {'form': form, 'title': f'Editar {item.title}'})


@role_required(STAFF_VIEW_ROLES)
def schedule_list(request):
    schedules = ClassSchedule.objects.select_related('content_item').all()
    return render(request, 'curriculum/schedule_list.html', {'schedules': schedules, 'title': 'Cronograma'})


@role_required(STAFF_VIEW_ROLES)
def schedule_new(request):
    form = ClassScheduleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        sched = form.save(commit=False)
        sched.created_by_user = request.user
        sched.save()
        messages.success(request, 'Cronograma criado.')
        return redirect('curriculum-schedule')
    return render(request, 'curriculum/schedule_form.html', {'form': form, 'title': 'Novo cronograma'})


@role_required(PROGRESS_MARK_ROLE)
def progress_mark(request):
    class_groups = list(_class_groups())
    form = ProgressSelectionForm(request.POST or None, class_groups=class_groups)
    children = []
    content_item = None

    if request.method == 'POST' and form.is_valid():
        class_group = form.cleaned_data['class_group']
        content_item = form.cleaned_data['content_item']
        children = list(Child.objects.filter(class_group=class_group, active=True).order_by('name'))

        if 'save' in request.POST:
            updated = 0
            with transaction.atomic():
                for child in children:
                    status_val = request.POST.get(f'status_{child.id}')
                    note_val = request.POST.get(f'note_{child.id}', '').strip()
                    if status_val:
                        obj, _ = ChildProgress.objects.get_or_create(child=child, content_item=content_item)
                        obj.status = status_val
                        obj.note = note_val
                        obj.marked_by_user = request.user
                        obj.marked_at = timezone.now()
                        obj.save()
                        updated += 1
            messages.success(request, f'Progresso atualizado para {updated} aventureiro(s).')
            return redirect('curriculum-progress')
    return render(
        request,
        'curriculum/progress_mark.html',
        {
            'form': form,
            'children': children,
            'content_item': content_item,
            'title': 'Marcar progresso',
        },
    )


@role_required(STAFF_VIEW_ROLES + RESP_ROLE)
def child_progress(request, child_id):
    child = get_object_or_404(Child, pk=child_id)
    if not _child_accessible(request.user, child):
        return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)
    progress = ChildProgress.objects.filter(child=child).select_related('content_item').order_by('content_item__order')
    return render(
        request,
        'curriculum/child_progress.html',
        {'child': child, 'progress': progress, 'title': f'Progresso de {child.name}'},
    )


@role_required(RESP_ROLE)
def my_progress(request):
    guardian_links = GuardianChild.objects.filter(guardian_user=request.user).select_related('child')
    children = [link.child for link in guardian_links]
    progress_map = {
        child.id: ChildProgress.objects.filter(child=child).select_related('content_item').order_by('content_item__order')
        for child in children
    }
    return render(
        request,
        'curriculum/my_progress.html',
        {'children': children, 'progress_map': progress_map, 'title': 'Apostila / Progresso'},
    )
