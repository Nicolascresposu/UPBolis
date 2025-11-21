from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_tokens = models.PositiveIntegerField()
    active = models.BooleanField(default=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    def __str__(self):
        return f"{self.name} ({self.price_tokens} UPBT)"


class UserTokenAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="token_account")
    token_balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"TokenAccount of {self.user.username}: {self.token_balance} UPBT"


@receiver(post_save, sender=User)
def create_user_token_account(sender, instance, created, **kwargs):
    if created:
        UserTokenAccount.objects.create(user=instance)


class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchases")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_tokens = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} bought {self.quantity} x {self.product.name}"
