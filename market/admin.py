from django.contrib import admin
from .models import Product, UserTokenAccount, Purchase, TokenTopUp


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price_tokens", "active")
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(UserTokenAccount)
class UserTokenAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "token_balance")
    search_fields = ("user__username",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity", "total_tokens", "created_at")
    list_filter = ("created_at",)


@admin.register(TokenTopUp)
class TokenTopUpAdmin(admin.ModelAdmin):
    list_display = ("user", "amount_tokens", "created_at", "description")
    list_filter = ("created_at",)
    search_fields = ("user__username",)