from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import F

from .forms import SignUpForm
from .models import Product, Purchase, UserTokenAccount


def home(request):
    return redirect("product_list")


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # UserTokenAccount is created by signal
            login(request, user)
            messages.success(request, "Account created! Welcome to UPBToken.")
            return redirect("product_list")
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})


def product_list(request):
    products = Product.objects.filter(active=True)
    return render(request, "product_list.html", {"products": products})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    return render(request, "product_detail.html", {"product": product})


@login_required
@transaction.atomic
def buy_product(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)

    if request.method != "POST":
        # Only allow POST
        return redirect("product_detail", pk=product.pk)

    quantity = int(request.POST.get("quantity", 1))
    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("product_detail", pk=product.pk)

    account = request.user.token_account
    total_cost = product.price_tokens * quantity

    # Reload account with lock to avoid race conditions
    account = UserTokenAccount.objects.select_for_update().get(pk=account.pk)

    if account.token_balance < total_cost:
        messages.error(request, "Not enough UPBTokens to buy this product.")
        return redirect("product_detail", pk=product.pk)

    # Deduct tokens
    account.token_balance = F("token_balance") - total_cost
    account.save()

    Purchase.objects.create(
        user=request.user,
        product=product,
        quantity=quantity,
        total_tokens=total_cost,
    )

    messages.success(
        request,
        f"You bought {quantity} x {product.name} for {total_cost} UPBTokens."
    )
    return redirect("dashboard")


@login_required
def dashboard(request):
    account = request.user.token_account
    purchases = request.user.purchases.select_related("product").order_by("-created_at")
    return render(
        request,
        "dashboard.html",
        {"account": account, "purchases": purchases},
    )
