import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from accounts.utils import normalize_whatsapp_number

from accounts.models import User
from .forms import AdventureLoginForm, UserCreateForm, UserEditForm
from .permissions import role_required
from .utils import redirect_for_role, get_available_roles
from children.models import Child, GuardianChild, ChildHealth
from children.forms import ChildForm
from children.utils import collect_children_payload, create_child_with_health

ROLE_GROUP_MAP = {
    'DIRETORIA': 'Diretoria',
    'SECRETARIA': 'Secretaria',
    'TESOUREIRO': 'Tesoureiro',
    'PROFESSOR': 'Professor',
    'RESPONSAVEL': 'Responsavel',
    'ADM': 'ADM',
}


def assign_user_groups(user, roles):
    names = {ROLE_GROUP_MAP.get(role) for role in roles if ROLE_GROUP_MAP.get(role)}
    groups = [Group.objects.get_or_create(name=name)[0] for name in names]
    user.groups.set(groups)


@never_cache
@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AdventureLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        whatsapp_number = form.cleaned_data['whatsapp_number']
        password = form.cleaned_data['password']

        user = authenticate(request, whatsapp_number=whatsapp_number, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login realizado com sucesso!', extra_tags='auth')
            request.session['active_role'] = getattr(user, 'role', None)
            request.session['available_roles'] = get_available_roles(user)
            return redirect('dashboard')

        pending_user = User.objects.filter(whatsapp_number=whatsapp_number).first()
        if pending_user and not pending_user.is_active:
            messages.error(
                request,
                'Cadastro recebido, mas aguarda ativação pela diretoria/ADM.',
            )
        else:
            messages.error(request, 'Número ou senha não conferem. Tente novamente.')

    return render(request, 'core/login.html', {'form': form})


@login_required
def dashboard(request):
    active = request.session.get('active_role') or getattr(request.user, 'role', None)
    request.user.active_role = active
    return redirect(redirect_for_role(request.user))


@role_required([User.Role.DIRETORIA])
def dashboard_diretoria(request):
    return render(request, 'dashboards/diretoria.html', {'title': 'Diretoria'})


@role_required([User.Role.SECRETARIA])
def dashboard_secretaria(request):
    return render(request, 'dashboards/secretaria.html', {'title': 'Secretaria'})


@role_required([User.Role.TESOUREIRO])
def dashboard_tesoureiro(request):
    return render(request, 'dashboards/tesoureiro.html', {'title': 'Tesoureiro'})


@role_required([User.Role.PROFESSOR])
def dashboard_professor(request):
    return render(request, 'dashboards/professor.html', {'title': 'Professor'})


@role_required([User.Role.RESPONSAVEL])
def dashboard_responsavel(request):
    return render(request, 'dashboards/responsavel.html', {'title': 'Responsável'})


@role_required([User.Role.ADM])
def config_view(request):
    return render(request, 'core/config.html')


@role_required([User.Role.DIRETORIA, User.Role.ADM])
def director_reports(request):
    UserModel = get_user_model()
    from finance.models import Fee
    from points.models import PointsLedger
    from attendance.models import AttendanceSession, AttendanceRecord

    users_count = UserModel.objects.count()
    users_by_role = UserModel.objects.values('role').annotate(total=models.Count('id'))
    children_count = Child.objects.count()
    children_by_class = Child.objects.values('class_group').annotate(total=models.Count('id'))

    fees = Fee.objects.all()
    fee_counts = fees.values('status').annotate(total=models.Count('id'))
    fee_totals = fees.aggregate(
        total_amount=models.Sum('amount'),
        total_discount=models.Sum('discount_amount'),
        total_final=models.Sum('final_amount'),
    )

    points_total = PointsLedger.objects.aggregate(total=models.Sum('points'))['total'] or 0

    sessions_count = AttendanceSession.objects.count()
    attendance_marked = AttendanceRecord.objects.count()

    context = {
        'title': 'Relatórios',
        'users_count': users_count,
        'users_by_role': users_by_role,
        'children_count': children_count,
        'children_by_class': children_by_class,
        'fee_counts': fee_counts,
        'fee_totals': fee_totals,
        'points_total': points_total,
        'sessions_count': sessions_count,
        'attendance_marked': attendance_marked,
    }
    return render(request, 'core/director_reports.html', context)


def logout_view(request):
    logout(request)
    messages.success(request, 'Você saiu da aventura. Volte sempre!', extra_tags='auth')
    return redirect('login')


@login_required
def switch_role(request, role):
    available = get_available_roles(request.user)
    if role in available:
        request.session['active_role'] = role
        request.user.active_role = role
        messages.success(request, f'Perfil ativo alterado para {role}.', extra_tags='role_switch')
    else:
        messages.error(request, 'Perfil não permitido para este usuário.')
    return redirect('dashboard')


@role_required([User.Role.DIRETORIA, User.Role.ADM])
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Usuário {user.whatsapp_number} criado/atualizado.')
        return redirect('user-create')
    return render(request, 'core/user_create.html', {'form': form, 'title': 'Novo usuário'})


@role_required([User.Role.DIRETORIA, User.Role.ADM])
def user_list(request):
    UserModel = get_user_model()
    role = request.GET.get('role', '')
    search = request.GET.get('q', '').strip()
    child_search = request.GET.get('child', '').strip()
    child_class = request.GET.get('class', '').strip()

    qs = UserModel.objects.all()
    if role:
        qs = qs.filter(role=role)
    if search:
        qs = qs.filter(
            models.Q(first_name__icontains=search)
            | models.Q(last_name__icontains=search)
            | models.Q(whatsapp_number__icontains=search)
        )
    qs = qs.order_by('first_name', 'whatsapp_number')

    children = Child.objects.all()
    if child_class:
        children = children.filter(class_group=child_class)
    if child_search:
        children = children.filter(name__icontains=child_search)
    children = children.order_by('class_group', 'name')

    class_options = [
        'Abelhinhas Laboriosas',
        'Luminares',
        'Edificadores',
        'Mãos Ajudadoras',
    ]
    return render(
        request,
        'core/user_list.html',
        {
            'users': qs,
            'children': children,
            'selected_role': role,
            'search': search,
            'child_search': child_search,
            'child_class': child_class,
            'class_options': class_options,
            'title': 'Usuários e Aventureiros',
        },
    )


@role_required([User.Role.DIRETORIA, User.Role.ADM])
def user_edit(request, pk):
    UserModel = get_user_model()
    user = get_object_or_404(UserModel, pk=pk)
    form = UserEditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Usuário atualizado.')
        return redirect('user-list')
    return render(request, 'core/user_edit.html', {'form': form, 'title': 'Editar usuário'})


@role_required([User.Role.DIRETORIA, User.Role.ADM])
@require_POST
def user_activate(request, pk):
    UserModel = get_user_model()
    user = get_object_or_404(UserModel, pk=pk)
    if user.is_active:
        messages.info(request, 'Usuário já está ativo.')
    else:
        user.is_active = True
        user.save()
        messages.success(request, f'Cadastro de {user.full_name or user.whatsapp_number} ativado.')
    return redirect('user-list')


@role_required([User.Role.DIRETORIA, User.Role.ADM, User.Role.SECRETARIA])
def child_edit(request, pk):
    child = get_object_or_404(Child, pk=pk)
    form = ChildForm(request.POST or None, instance=child)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Aventureiro atualizado.')
        return redirect('user-list')
    return render(request, 'core/child_edit.html', {'form': form, 'title': 'Editar aventureiro'})


@role_required([User.Role.DIRETORIA, User.Role.SECRETARIA, User.Role.TESOUREIRO, User.Role.PROFESSOR, User.Role.RESPONSAVEL, User.Role.ADM])
def child_overview(request, pk):
    child = get_object_or_404(Child, pk=pk)
    # Restringe responsáveis aos seus próprios aventureiros
    if getattr(request.user, 'role', None) == User.Role.RESPONSAVEL:
        if not GuardianChild.objects.filter(guardian_user=request.user, child=child).exists():
            return render(request, '403.html', {'back_url': '/dashboard/'}, status=403)

    from finance.models import Fee
    from points.models import PointsLedger
    from attendance.models import AttendanceRecord
    from curriculum.models import ChildProgress
    from documents.models import ChildDocument

    fees = list(Fee.objects.filter(child=child).order_by('-reference_month')[:6])
    points_qs = PointsLedger.objects.filter(child=child).order_by('-created_at')
    points_last = list(points_qs.select_related('created_by_user')[:5])
    points_total = points_qs.aggregate(total=models.Sum('points'))['total'] or 0
    attendance_last = list(
        AttendanceRecord.objects.filter(child=child).select_related('session', 'marked_by_user').order_by('-marked_at')[:5]
    )
    documents = list(ChildDocument.objects.filter(child=child).order_by('-updated_at')[:5])
    progress_records = list(ChildProgress.objects.filter(child=child).order_by('-marked_at')[:5])
    guardians = GuardianChild.objects.filter(child=child).select_related('guardian_user')

    context = {
        'title': f'Aventureiro {child.name}',
        'child': child,
        'fees': fees,
        'points_last': points_last,
        'points_total': points_total,
        'attendance_last': attendance_last,
        'documents': documents,
        'progress_records': progress_records,
        'guardians': guardians,
    }
    return render(request, 'children/overview.html', context)


def signup(request):
    UserModel = get_user_model()
    directoria_candidates = UserModel.objects.filter(role__in=[User.Role.ADM, User.Role.DIRETORIA]).order_by('first_name')
    role_choices = User.Role.choices
    if request.method == 'POST':
        signup_type = request.POST.get('signup_type', 'responsavel')
        if signup_type == 'directoria':
            dir_name = request.POST.get('dir_name', '').strip()
            dir_last = request.POST.get('dir_last', '').strip()
            dir_whatsapp = request.POST.get('dir_whatsapp', '').strip()
            dir_email = request.POST.get('dir_email', '').strip()
            dir_address = request.POST.get('dir_address', '').strip()
            dir_password = request.POST.get('dir_password', '').strip()
            dir_password_confirm = request.POST.get('dir_password_confirm', '').strip()
            dir_roles = request.POST.getlist('dir_roles')

            errors = []
            if not (dir_name and dir_whatsapp and dir_password and dir_password_confirm):
                errors.append('Informe nome, WhatsApp e senha para o cadastro da diretoria.')
            if dir_password and dir_password_confirm and dir_password != dir_password_confirm:
                errors.append('As senhas informadas para a diretoria não conferem.')
            if not dir_roles:
                errors.append('Selecione pelo menos um perfil.')

            dir_whatsapp_norm = normalize_whatsapp_number(dir_whatsapp)
            if not dir_whatsapp_norm:
                errors.append('WhatsApp inválido para o membro da diretoria.')

            if errors:
                for err in errors:
                    messages.error(request, err)
                return render(
                    request,
                    'core/signup.html',
                    {
                        'title': 'Cadastre-se',
                        'directoria_candidates': directoria_candidates,
                        'role_choices': role_choices,
                    },
                )

            user, created = UserModel.objects.get_or_create(
                whatsapp_number=dir_whatsapp_norm,
                defaults={
                    'first_name': dir_name,
                    'last_name': dir_last,
                    'role': dir_roles[0],
                    'financial_whatsapp': dir_whatsapp_norm,
                    'financial_phone': '',
                    'address': dir_address,
                    'email': dir_email,
                    'is_staff': True,
                },
            )
            user.first_name = dir_name
            user.last_name = dir_last
            user.financial_whatsapp = dir_whatsapp_norm
            user.financial_phone = ''
            user.email = dir_email
            user.role = dir_roles[0]
            user.is_staff = True
            user.is_superuser = User.Role.ADM in dir_roles
            if created:
                user.is_active = False
            user.set_password(dir_password)
            user.save()
            assign_user_groups(user, dir_roles)
            messages.success(
                request,
                'Responsável administrativo cadastrado com sucesso e aguarda ativação da diretoria/ADM.',
            )
            return redirect('login')
        # Dados do responsável
        resp_name = request.POST.get('resp_name', '').strip()
        resp_last = request.POST.get('resp_last', '').strip()
        resp_whatsapp = request.POST.get('resp_whatsapp', '').strip()
        resp_fin_whatsapp = request.POST.get('resp_fin_whatsapp', '').strip()
        resp_fin_phone = request.POST.get('resp_fin_phone', '').strip()
        resp_cpf = request.POST.get('resp_cpf', '').strip()
        resp_address = request.POST.get('resp_address', '').strip()
        resp_email = request.POST.get('resp_email', '').strip()
        resp_password = request.POST.get('resp_password', '').strip()
        resp_password_confirm = request.POST.get('resp_password_confirm', '').strip()
        resp_password_confirm = request.POST.get('resp_password_confirm', '').strip()

        # Autorizações obrigatórias
        errors = []
        children_payload, child_errors = collect_children_payload(request.POST, request.FILES)
        errors.extend(child_errors)

        if not (resp_name and resp_whatsapp and resp_password and resp_cpf):
            errors.append('Preencha nome, WhatsApp, CPF e senha do responsável.')
        if resp_password and resp_password_confirm and resp_password != resp_password_confirm:
            errors.append('As senhas informadas não conferem.')

        resp_whatsapp_norm = normalize_whatsapp_number(resp_whatsapp)
        resp_fin_whatsapp_norm = normalize_whatsapp_number(resp_fin_whatsapp) if resp_fin_whatsapp else ''
        if not resp_whatsapp_norm:
            errors.append('WhatsApp do responsável inválido.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'core/signup.html')

        # cria usuário
        user, created = UserModel.objects.get_or_create(
            whatsapp_number=resp_whatsapp_norm,
            defaults={
                'first_name': resp_name,
                'last_name': resp_last,
                'role': User.Role.RESPONSAVEL,
                'financial_whatsapp': resp_fin_whatsapp_norm or resp_whatsapp_norm,
                'financial_phone': resp_fin_phone,
                'address': resp_address,
                'email': resp_email,
            },
        )
        user.first_name = resp_name
        user.last_name = resp_last
        user.financial_whatsapp = resp_fin_whatsapp_norm or resp_whatsapp_norm
        user.financial_phone = resp_fin_phone
        user.address = resp_address
        user.email = resp_email
        user.role = User.Role.RESPONSAVEL
        user.set_password(resp_password)
        user.save()

        # cria filhos + saúde + vínculo
        for payload in children_payload:
            create_child_with_health(user, payload)

        messages.success(request, 'Cadastro enviado! Login liberado e diretoria notificada.')
        return redirect('login')

    return render(
        request,
        'core/signup.html',
        {
            'title': 'Cadastre-se',
            'directoria_candidates': directoria_candidates,
            'role_choices': role_choices,
        },
    )
