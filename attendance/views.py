from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from children.models import Child, GuardianChild
from core.permissions import role_required

from .forms import AttendanceSessionForm
from .models import AttendanceRecord, AttendanceSession

UserModel = get_user_model()

STAFF_ROLES = [
    User.Role.DIRETORIA,
    User.Role.SECRETARIA,
    User.Role.TESOUREIRO,
    User.Role.PROFESSOR,
]


@role_required(STAFF_ROLES)
def session_list(request):
    sessions = AttendanceSession.objects.all()
    return render(request, 'attendance/sessions_list.html', {'sessions': sessions, 'title': 'Sessões de Presença'})


@role_required(STAFF_ROLES)
def session_create(request):
    form = AttendanceSessionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        session = form.save(commit=False)
        session.created_by_user = request.user
        session.save()
        messages.success(request, 'Sessão criada com sucesso.')
        return redirect('attendance-sessions')
    return render(request, 'attendance/session_form.html', {'form': form, 'title': 'Nova Sessão'})


@role_required(STAFF_ROLES)
def take_attendance(request, pk):
    session = get_object_or_404(AttendanceSession, pk=pk)
    children_qs = Child.objects.filter(active=True)
    if session.class_group:
        children_qs = children_qs.filter(class_group=session.class_group)
    children = children_qs.order_by('name')

    if request.method == 'POST':
        for child in children:
            present_val = request.POST.get(f'present_{child.id}') == 'on'
            note_val = request.POST.get(f'note_{child.id}', '').strip()
            record, _ = AttendanceRecord.objects.get_or_create(session=session, child=child)
            record.present = present_val
            record.note = note_val
            record.marked_by_user = request.user
            record.marked_at = timezone.now()
            record.save()
        messages.success(request, 'Presenças registradas.')
        return redirect('attendance-sessions')

    records_map = {
        rec.child_id: rec for rec in AttendanceRecord.objects.filter(session=session)
    }
    return render(
        request,
        'attendance/take_attendance.html',
        {
            'session': session,
            'children': children,
            'records_map': records_map,
            'title': 'Chamada de Presença',
        },
    )


@role_required([User.Role.RESPONSAVEL])
def my_attendance(request):
    guardian_links = GuardianChild.objects.filter(guardian_user=request.user).select_related('child')
    children = [link.child for link in guardian_links]
    records = (
        AttendanceRecord.objects.filter(child__in=children)
        .select_related('session', 'child')
        .order_by('-session__date', 'child__name')
    )
    return render(
        request,
        'attendance/my_attendance.html',
        {'records': records, 'title': 'Presença dos meus aventureiros'},
    )
