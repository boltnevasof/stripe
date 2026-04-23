from decimal import Decimal

from django.db import models


CURRENCY_CHOICES = [
    ("usd", "USD"),
    ("eur", "EUR"),
]


class Item(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="usd")

    def __str__(self):
        return self.name

    def price_in_cents(self):
        # Stripe хочет целое число в минимальных единицах валюты (центы/евроценты)
        return int(self.price * 100)


class Discount(models.Model):
    """Купон для Stripe. Можно задать либо процент, либо фиксированную сумму."""
    name = models.CharField(max_length=100)
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    amount_off = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="usd")
    # ID купона в Stripe. Заполняется автоматически при первом использовании.
    stripe_coupon_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Tax(models.Model):
    """Налоговая ставка для Stripe."""
    name = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    inclusive = models.BooleanField(default=False, help_text="True — налог включён в цену")
    stripe_tax_rate_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"


class Order(models.Model):
    items = models.ManyToManyField(Item, related_name="orders")
    discount = models.ForeignKey(Discount, null=True, blank=True, on_delete=models.SET_NULL)
    taxes = models.ManyToManyField(Tax, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk}"

    def currency(self):
        first = self.items.first()
        return first.currency if first else "usd"

    def total(self):
        return sum((i.price for i in self.items.all()), Decimal("0"))
