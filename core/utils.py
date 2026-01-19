from django.urls import reverse

from accounts.models import User

ROLE_REDIRECTS = {
    User.Role.ADM: 'config',
    User.Role.DIRETORIA: 'dashboard-diretoria',
    User.Role.SECRETARIA: 'dashboard-secretaria',
    User.Role.TESOUREIRO: 'dashboard-tesoureiro',
    User.Role.PROFESSOR: 'dashboard-professor',
    User.Role.RESPONSAVEL: 'dashboard-responsavel',
}


def get_available_roles(user: User) -> list[str]:
    """Lista de roles que o usuário possui (role primária + grupos mapeados)."""
    roles = {getattr(user, 'role', None)}
    group_map = {
        'Diretoria': User.Role.DIRETORIA,
        'Secretaria': User.Role.SECRETARIA,
        'Tesoureiro': User.Role.TESOUREIRO,
        'Professor': User.Role.PROFESSOR,
        'Responsavel': User.Role.RESPONSAVEL,
        'ADM': User.Role.ADM,
    }
    for g in getattr(user, 'groups', []).all():
        role = group_map.get(g.name)
        if role:
            roles.add(role)
    return [r for r in roles if r]


def redirect_for_role(user: User):
    role = getattr(user, 'active_role', None) or getattr(user, 'role', None)
    name = ROLE_REDIRECTS.get(role, 'dashboard-responsavel')
    return reverse(name)
