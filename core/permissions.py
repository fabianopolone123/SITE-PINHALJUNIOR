from functools import wraps

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import User
from .utils import redirect_for_role, get_available_roles


def role_required(allowed_roles: list[str] | tuple[str, ...]):
    """
    Decorator to require authentication and specific roles.
    If not authenticated -> redirects to login with next param.
    If authenticated but not allowed -> renders 403 friendly page.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                login_url = f"{reverse('login')}?next={request.get_full_path()}"
                return redirect(login_url)

            available = get_available_roles(request.user)
            active_role = request.session.get('active_role') or getattr(request.user, 'role', None)
            if active_role not in available and available:
                active_role = available[0]
            if active_role not in allowed_roles:
                # Se o usuário tem algum dos roles permitidos, ativa automaticamente.
                match = next((r for r in available if r in allowed_roles), None)
                if match:
                    active_role = match
                    request.session['active_role'] = match
                else:
                    return render(
                        request,
                        '403.html',
                        status=403,
                        context={
                            'user': request.user,
                            'back_url': redirect_for_role(request.user),
                        },
                    )

            request.user.active_role = active_role
            request.session['active_role'] = active_role
            request.session['available_roles'] = available
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
