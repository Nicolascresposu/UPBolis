from functools import wraps
from django.shortcuts import redirect


def api_login_required(view_func):
    """
    Requiere que exista un token de la API en la sesión.
    Si no, manda a /login.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('api_token'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """
    Uso:
    @role_required('buyer')
    @role_required('seller', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.session.get('api_user')
            if not user:
                return redirect('login')
            role = str(user.get('role', '')).lower()
            if allowed_roles and role not in allowed_roles:
                # si no tiene rol, lo mando al dashboard genérico
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
