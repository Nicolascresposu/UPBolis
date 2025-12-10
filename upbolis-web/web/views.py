import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from datetime import datetime
from django.utils import timezone

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

    # Si no es 2xx, intentamos leer mensaje pero sin romper si no es JSON
    if not resp.ok:
        msg = "Credenciales inválidas o error en la API."
        try:
            data = resp.json()
            msg = data.get('message', msg)
        except ValueError:
            print("LOGIN API ERROR (no JSON):", resp.status_code, resp.text[:300])
        messages.error(request, msg)
        return render(request, 'login.html', status=resp.status_code)

    # Aquí la API devolvió 2xx, pero igual puede no ser JSON…
    try:
        data = resp.json()
    except ValueError:
        print("LOGIN API NON-JSON BODY:", resp.status_code, resp.text[:300])
        messages.error(request, "La API de login devolvió una respuesta no válida.")
        return render(request, 'login.html', status=500)

    # Tomamos token y user del JSON
    token = data.get('token')
    user = data.get('user') or data  # por si el controlador devuelve directamente el user

    if not token or not user:
        print("LOGIN API INVALID DATA:", data)
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

    # Destinatarios posibles (combo)
    recipients = []
    try:
        r = requests.get(f"{API_BASE}/wallet/recipients", headers=headers)
        if r.status_code == 200:
            data = r.json() or {}
            recipients = data.get('recipients', []) or []
    except Exception:
        recipients = []

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

    # Opcional: formatear fechas de órdenes y transacciones
    orders_display = []
    for o in orders:
        o_copy = dict(o)
        o_copy['created_at_display'] = _format_iso_datetime(o.get('created_at'))
        orders_display.append(o_copy)

    tx_display = []
    for tx in transactions:
        t_copy = dict(tx)
        t_copy['created_at_display'] = _format_iso_datetime(tx.get('created_at'))
        tx_display.append(t_copy)

    return render(request, 'buyer_dashboard.html', {
        'user_name': request.session.get('api_user', {}).get('name'),
        'wallet': wallet,
        'products': products,
        'orders': orders_display,
        'transactions': tx_display,
        'stats': stats,
        'recipients': recipients,
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
    wallet = {}
    try:
        r = requests.get(f"{API_BASE}/wallet", headers=headers)
        if r.status_code == 200:
            wallet = r.json().get('wallet', {}) or {}
    except Exception:
        wallet = {}

    products = []
    try:
        r = requests.get(f"{API_BASE}/seller/products", headers=headers)
        if r.status_code == 200:
            products = r.json() or []
    except Exception:
        products = []

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

    users = []
    try:
        r = requests.get(f"{API_BASE}/admin/users", headers=headers)
        if r.status_code == 200:
            users = r.json() or []
    except Exception:
        users = []

    orders = []
    try:
        r = requests.get(f"{API_BASE}/admin/orders", headers=headers)
        if r.status_code == 200:
            orders = r.json() or []
    except Exception:
        orders = []

    transactions = []
    try:
        r = requests.get(f"{API_BASE}/admin/transactions", headers=headers)
        if r.status_code == 200:
            transactions = r.json() or []
    except Exception:
        transactions = []

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

    orders_display = []
    for o in orders:
        o_copy = dict(o)
        o_copy['created_at_display'] = _format_iso_datetime(o.get('created_at'))
        orders_display.append(o_copy)

    tx_display = []
    for tx in transactions:
        t_copy = dict(tx)
        t_copy['created_at_display'] = _format_iso_datetime(tx.get('created_at'))
        tx_display.append(t_copy)

    return render(request, 'admin_dashboard.html', {
        'user': request.session.get('api_user'),
        'users': users,
        'orders': orders_display,
        'transactions': tx_display,
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


@api_login_required
@role_required('admin')
@require_POST
def admin_create_user(request):
    """
    Crear usuario nuevo usando /auth/register, permitiendo definir contraseña
    y, opcionalmente, cargar saldo inicial con /admin/wallets/{user}/deposit
    """
    token = request.session.get('api_token')
    admin_headers = {"Authorization": f"Bearer {token}"}

    name = request.POST.get("name")
    email = request.POST.get("email")
    role = request.POST.get("role", "buyer")
    initial_balance_raw = request.POST.get("initial_balance") or "0"

    raw_pass = request.POST.get("password") or ""
    raw_conf = request.POST.get("password_confirmation") or ""

    used_default_password = False
    default_password = "UPBolis1234"

    if not raw_pass and not raw_conf:
        password = default_password
        password_confirmation = default_password
        used_default_password = True
    else:
        if raw_pass != raw_conf:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect("admin_dashboard")
        password = raw_pass
        password_confirmation = raw_conf

    payload = {
        "name": name,
        "email": email,
        "password": password,
        "password_confirmation": password_confirmation,
        "role": role,
    }

    try:
        resp = requests.post(
            f"{API_BASE}/auth/register",
            json=payload,
        )

        print("REGISTER RESP STATUS:", resp.status_code)
        print("REGISTER RESP BODY:", resp.text[:1000])

        if resp.status_code not in (200, 201):
            try:
                data = resp.json()
                msg = data.get("message") or str(data)
            except Exception:
                msg = resp.text[:300] or "No se pudo crear el usuario."
            messages.error(request, f"Error al crear usuario: {msg}")
            return redirect("admin_dashboard")

        data = resp.json()
        user_data = data.get("user") if isinstance(data, dict) and "user" in data else data
        user_id = user_data.get("id") if isinstance(user_data, dict) else None

        try:
            initial_balance = float(initial_balance_raw)
        except ValueError:
            initial_balance = 0

        if used_default_password:
            base_msg = f"Usuario creado correctamente con contraseña por defecto {default_password}."
        else:
            base_msg = "Usuario creado correctamente con la contraseña indicada."

        if user_id and initial_balance > 0:
            dep_resp = requests.post(
                f"{API_BASE}/admin/wallets/{user_id}/deposit",
                headers=admin_headers,
                json={
                    "amount": initial_balance,
                    "reason": "Saldo inicial desde panel de admin",
                },
            )
            print("DEPOSIT RESP STATUS:", dep_resp.status_code)
            print("DEPOSIT RESP BODY:", dep_resp.text[:500])

            if dep_resp.status_code not in (200, 201):
                messages.warning(
                    request,
                    base_msg + " Sin embargo, no se pudo cargar el saldo inicial."
                )
            else:
                messages.success(
                    request,
                    base_msg + f" Además, se cargaron {initial_balance} UPBolis."
                )
        else:
            messages.success(request, base_msg)

    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")
        print("REGISTER EXCEPTION:", repr(e))

    return redirect("admin_dashboard")


@api_login_required
@role_required('admin')
@require_POST
def admin_topup_tokens(request):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    user_id = request.POST.get("user_id")
    amount_raw = request.POST.get("amount")
    reason = request.POST.get("reason") or "Carga manual desde panel admin"

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0

    if not user_id or amount <= 0:
        messages.error(request, "Debes seleccionar un usuario y un monto válido.")
        return redirect("admin_dashboard")

    try:
        resp = requests.post(
            f"{API_BASE}/admin/wallets/{user_id}/deposit",
            headers=headers,
            json={
                "amount": amount,
                "reason": reason,
            },
        )
        if resp.status_code not in (200, 201):
            try:
                data = resp.json()
                msg = data.get("message", "No se pudo cargar UPBolis al usuario.")
            except Exception:
                msg = "No se pudo cargar UPBolis al usuario."
            messages.error(request, msg)
        else:
            messages.success(request, f"Se cargaron {amount} UPBolis al usuario.")
    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")

    return redirect("admin_dashboard")


@api_login_required
@role_required('admin')
@require_POST
def admin_manage_user(request, user_id):
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    role = request.POST.get("role")
    amount_raw = request.POST.get("amount") or "0"
    operation = request.POST.get("operation") or "deposit"
    reason = request.POST.get("reason") or "Ajuste manual desde panel admin"

    actions_ok = []
    errors = []

    if role:
        try:
            r_role = requests.patch(
                f"{API_BASE}/admin/users/{user_id}/role",
                headers=headers,
                json={"role": role},
            )
            if r_role.status_code not in (200, 204):
                try:
                    data = r_role.json()
                    msg = data.get("message", "No se pudo actualizar el rol.")
                except Exception:
                    msg = "No se pudo actualizar el rol."
                errors.append(msg)
            else:
                actions_ok.append("Rol actualizado")
        except Exception as e:
            errors.append(f"Error al actualizar el rol: {e}")

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = 0

    if amount > 0:
        endpoint = "deposit" if operation == "deposit" else "withdraw"
        try:
            r_wallet = requests.post(
                f"{API_BASE}/admin/wallets/{user_id}/{endpoint}",
                headers=headers,
                json={"amount": amount, "reason": reason},
            )
            if r_wallet.status_code not in (200, 201):
                try:
                    data = r_wallet.json()
                    msg = data.get("message", "No se pudo ajustar el saldo del usuario.")
                except Exception:
                    msg = "No se pudo ajustar el saldo del usuario."
                errors.append(msg)
            else:
                verb = "añadidos" if endpoint == "deposit" else "restados"
                actions_ok.append(f"Saldo {verb} ({amount} UPBolis)")
        except Exception as e:
            errors.append(f"Error al ajustar el saldo: {e}")

    if actions_ok:
        messages.success(request, " · ".join(actions_ok))
    if errors and not actions_ok:
        messages.error(request, " | ".join(errors))
    elif errors:
        messages.warning(request, " · ".join(errors))

    return redirect("admin_dashboard")


def _format_iso_datetime(value):
    """
    Convierte '2025-12-10T17:19:34.000000Z' a '10/12/2025 13:19'
    (ajustado a la zona horaria de Django).
    """
    if not value:
        return value
    try:
        if isinstance(value, str):
            s = value.rstrip('Z')
            dt = datetime.fromisoformat(s)
        else:
            return value

        if timezone.is_naive(dt):
            dt = dt.replace(tzinfo=timezone.utc)

        dt_local = dt.astimezone(timezone.get_current_timezone())
        return dt_local.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return value


# ========== WALLET TRANSFER (Django -> Laravel) ==========

@api_login_required
@role_required('buyer', 'seller', 'admin')
@require_POST
def wallet_transfer(request):
    """
    Transferir UPBolis desde la wallet del usuario logueado hacia otro usuario.
    Envía la petición a POST /wallet/transfer de la API Laravel.
    """
    token = request.session.get('api_token')
    headers = {"Authorization": f"Bearer {token}"}

    to_email = request.POST.get("to_email")
    amount_raw = request.POST.get("amount")
    reason = request.POST.get("reason") or "Transferencia desde panel web"

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0

    if not to_email or amount <= 0:
        messages.error(request, "Debes seleccionar un destinatario y un monto válido.")
        return redirect("buyer_dashboard")

    try:
        resp = requests.post(
            f"{API_BASE}/wallet/transfer",
            headers=headers,
            json={
                "to_email": to_email,
                "amount": amount,
                "reason": reason,
            },
        )

        print("WALLET TRANSFER STATUS:", resp.status_code)
        print("WALLET TRANSFER BODY:", resp.text[:400])

        if resp.status_code not in (200, 201):
            try:
                data = resp.json()
                msg = data.get("message") or str(data)
            except Exception:
                msg = "No se pudo realizar la transferencia."
            messages.error(request, msg)
        else:
            try:
                data = resp.json()
                msg = data.get("message", "Transferencia realizada correctamente.")
            except Exception:
                msg = "Transferencia realizada correctamente."
            messages.success(request, msg)

    except Exception as e:
        messages.error(request, f"Error al conectar con la API: {e}")

    return redirect("buyer_dashboard")
