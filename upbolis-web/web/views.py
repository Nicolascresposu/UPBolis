import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods

from .utils import api_login_required, role_required

API_BASE = settings.API_BASE_URL


def redirect_to_login(request):
    return redirect('login')


# ========== AUTH ==========

def login_view(request):
    # GET: mostrar formulario
    if request.method == 'GET':
        if request.session.get('api_token') and request.session.get('api_user'):
            return redirect('dashboard')
        return render(request, 'login.html')

    # POST: procesar login contra Laravel
    email = request.POST.get('email')
    password = request.POST.get('password')

    try:
        resp = requests.post(f"{API_BASE}/auth/login", json={
            "email": email,
            "password": password,
        })
    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")
        return render(request, 'login.html', status=500)

    if resp.status_code != 200:
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass
        msg = data.get('message', 'Credenciales inválidas o error en la API.')
        messages.error(request, msg)
        return render(request, 'login.html', status=401)

    data = resp.json()
    token = data.get('token')
    user = data.get('user')

    if not token or not user:
        messages.error(request, 'Respuesta inválida de la API de login.')
        return render(request, 'login.html', status=500)

    # Guardar en sesión
    request.session['api_token'] = token
    request.session['api_user'] = user

    # Redirigir según rol
    role = str(user.get('role', '')).lower()
    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'seller':
        return redirect('seller_dashboard')
    else:
        return redirect('buyer_dashboard')


def logout_view(request):
    token = request.session.get('api_token')
    if token:
        try:
            requests.post(
                f"{API_BASE}/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
        except Exception:
            # ignoramos errores
            pass

    request.session.flush()
    return redirect('login')


# ========== DASHBOARD GENÉRICO ==========

@api_login_required
def dashboard_view(request):
    """
    Dashboard genérico que redirige según el rol del usuario.
    """
    user = request.session.get('api_user', {})
    role = str(user.get('role', '')).lower()

    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'seller':
        return redirect('seller_dashboard')
    else:
        return redirect('buyer_dashboard')


# ========== BUYER DASHBOARD ==========

@api_login_required
@role_required('buyer')
def buyer_dashboard(request):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    # Wallet
    wallet = {}
    try:
        r = requests.get(f"{API_BASE}/wallet", headers=headers)
        if r.status_code == 200:
            wallet = r.json().get('wallet', {}) or {}
    except Exception:
        wallet = {}

    # Productos
    products = []
    try:
        r = requests.get(f"{API_BASE}/products", headers=headers)
        if r.status_code == 200:
            products = r.json() or []
    except Exception:
        products = []

    # Órdenes del buyer
    orders = []
    try:
        r = requests.get(f"{API_BASE}/orders", headers=headers)
        if r.status_code == 200:
            orders = r.json() or []
    except Exception:
        orders = []

    # Transacciones de MI wallet
    transactions = []
    try:
        r = requests.get(f"{API_BASE}/transactions", headers=headers)
        if r.status_code == 200:
            transactions = r.json() or []
    except Exception:
        transactions = []

    # Stats simples
    total_spent = 0
    try:
        total_spent = sum(float(o.get('total', 0)) for o in orders)
    except Exception:
        total_spent = 0

    stats = {
        "total_orders": len(orders),
        "total_spent": total_spent,
    }

    return render(request, 'buyer_dashboard.html', {
        'user_name': request.session.get('api_user', {}).get('name'),
        'wallet': wallet,
        'products': products,
        'orders': orders,
        'transactions': transactions,
        'stats': stats,
    })


# ========== SELLER DASHBOARD ==========

@api_login_required
@role_required('seller', 'admin')
@require_http_methods(["GET", "POST"])
def seller_dashboard(request):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    # Si viene POST desde el modal: crear producto
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        description = request.POST.get("description")

        try:
            resp = requests.post(
                f"{API_BASE}/seller/products",
                headers=headers,
                json={
                    "name": name,
                    "price": price,
                    "stock": stock,
                    "description": description,
                },
            )
            if resp.status_code not in (200, 201):
                try:
                    data = resp.json()
                    msg = data.get("message", "No se pudo crear el producto.")
                except Exception:
                    msg = "No se pudo crear el producto."
                messages.error(request, msg)
            else:
                messages.success(request, "Producto creado correctamente.")
        except Exception as e:
            messages.error(request, f"Error al conectar con la API: {e}")

        return redirect("seller_dashboard")

    # GET normal: cargar datos del seller
    # Wallet del seller
    wallet = {}
    try:
        r = requests.get(f"{API_BASE}/wallet", headers=headers)
        if r.status_code == 200:
            wallet = r.json().get('wallet', {}) or {}
    except Exception:
        wallet = {}

    # Productos del seller
    products = []
    try:
        r = requests.get(f"{API_BASE}/seller/products", headers=headers)
        if r.status_code == 200:
            products = r.json() or []
    except Exception:
        products = []

    # Órdenes de mis productos
    orders = []
    try:
        r = requests.get(f"{API_BASE}/seller/orders", headers=headers)
        if r.status_code == 200:
            orders = r.json() or []
    except Exception:
        orders = []

    stats = {
        "total_products": len(products),
        "total_orders": len(orders),
    }

    return render(request, 'seller_dashboard.html', {
        'user': request.session.get('api_user'),
        'wallet': wallet,
        'products': products,
        'orders': orders,
        'stats': stats,
    })


# DELETE de producto (desde el botón "Eliminar")
@api_login_required
@role_required('seller', 'admin')
@require_POST
def seller_delete_product(request, product_id):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.delete(
            f"{API_BASE}/seller/products/{product_id}",
            headers=headers,
        )
        if resp.status_code not in (200, 204):
            try:
                data = resp.json()
                msg = data.get("message", "No se pudo eliminar el producto.")
            except Exception:
                msg = "No se pudo eliminar el producto."
            messages.error(request, msg)
        else:
            messages.success(request, "Producto eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")

    return redirect("seller_dashboard")


# ========== ADMIN DASHBOARD ==========

@api_login_required
@role_required('admin')
def admin_dashboard(request):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    # Usuarios
    users = []
    try:
        r = requests.get(f"{API_BASE}/admin/users", headers=headers)
        if r.status_code == 200:
            users = r.json() or []
    except Exception:
        users = []

    # Órdenes globales
    orders = []
    try:
        r = requests.get(f"{API_BASE}/admin/orders", headers=headers)
        if r.status_code == 200:
            orders = r.json() or []
    except Exception:
        orders = []

    # Transacciones globales
    transactions = []
    try:
        r = requests.get(f"{API_BASE}/admin/transactions", headers=headers)
        if r.status_code == 200:
            transactions = r.json() or []
    except Exception:
        transactions = []

    # Stats simples
    total_users = len(users)
    total_sellers = len([u for u in users if str(u.get('role', '')).lower() == 'seller'])
    total_orders = len(orders)
    total_volume = 0
    try:
        total_volume = sum(float(o.get('total', 0)) for o in orders)
    except Exception:
        total_volume = 0

    stats = {
        "total_users": total_users,
        "total_sellers": total_sellers,
        "total_orders": total_orders,
        "total_volume": total_volume,
    }

    return render(request, 'admin_dashboard.html', {
        'user': request.session.get('api_user'),
        'users': users,
        'orders': orders,
        'transactions': transactions,
        'stats': stats,
    })


# ========== ADMIN: ACCIONES SOBRE USUARIOS ==========

@api_login_required
@role_required('admin')
@require_POST
def admin_update_user_role(request, user_id):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    new_role = request.POST.get("role")

    try:
        resp = requests.patch(
            f"{API_BASE}/admin/users/{user_id}/role",
            headers=headers,
            json={"role": new_role},
        )
        if resp.status_code not in (200, 204):
            try:
                data = resp.json()
                msg = data.get("message", "No se pudo actualizar el rol.")
            except Exception:
                msg = "No se pudo actualizar el rol."
            messages.error(request, msg)
        else:
            messages.success(request, "Rol actualizado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")

    return redirect("admin_dashboard")


@api_login_required
@role_required('admin')
@require_POST
def admin_toggle_user_active(request, user_id):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.patch(
            f"{API_BASE}/admin/users/{user_id}/deactivate",
            headers=headers,
        )
        if resp.status_code not in (200, 204):
            try:
                data = resp.json()
                msg = data.get("message", "No se pudo cambiar el estado del usuario.")
            except Exception:
                msg = "No se pudo cambiar el estado del usuario."
            messages.error(request, msg)
        else:
            messages.success(request, "Estado del usuario actualizado.")
    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")

    return redirect("admin_dashboard")
