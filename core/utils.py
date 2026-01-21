from django.urls import reverse
import unicodedata

from accounts.models import User

ROLE_REDIRECTS = {
    User.Role.ADM: 'config',
    User.Role.DIRETORIA: 'dashboard-diretoria',
    User.Role.SECRETARIA: 'dashboard-secretaria',
    User.Role.TESOUREIRO: 'dashboard-tesoureiro',
    User.Role.PROFESSOR: 'dashboard-professor',
    User.Role.RESPONSAVEL: 'dashboard-responsavel',
}

ROLE_KEYWORDS = {
    User.Role.ADM: ['adm', 'administrador'],
    User.Role.DIRETORIA: ['diretor', 'diretoria'],
    User.Role.SECRETARIA: ['secretaria', 'secretario'],
    User.Role.TESOUREIRO: ['tesoureiro', 'tesouraria'],
    User.Role.PROFESSOR: ['professor', 'professores'],
    User.Role.RESPONSAVEL: ['responsavel', 'responsaveis'],
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value)
    return ''.join(ch for ch in normalized if ch.isalnum()).lower()


def _role_from_group_name(name: str) -> str | None:
    normalized = _normalize_text(name or '')
    for role, keywords in ROLE_KEYWORDS.items():
        for keyword in keywords:
            norm_keyword = _normalize_text(keyword)
            if norm_keyword and norm_keyword in normalized:
                return role
            return role
    return None


def get_available_roles(user: User) -> list[str]:
    """Lista de roles que o usuǭrio possui (role primǭria + grupos mapeados)."""
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
        role = group_map.get(g.name) or _role_from_group_name(g.name)
        if role:
            roles.add(role)
    return [r for r in roles if r]


def redirect_for_role(user: User):
    role = getattr(user, 'active_role', None) or getattr(user, 'role', None)
    name = ROLE_REDIRECTS.get(role, 'dashboard-responsavel')
    return reverse(name)
