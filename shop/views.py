"""Всё общение со Stripe живёт здесь.

Идея простая:
- по Item.currency выбираем нужную пару Stripe-ключей (STRIPE_KEYS[currency])
- передаём секретный ключ каждому вызову Stripe API через api_key=...
- публичный ключ отдаём в шаблон, чтобы Stripe.js инициализировался правильно
"""
import stripe
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Discount, Item, Order, Tax


def _stripe_keys(currency):
    keys = settings.STRIPE_KEYS.get(currency.lower())
    if not keys or not keys["secret"]:
        raise ValueError(
            f"Stripe-ключи для валюты {currency!r} не заданы. "
            f"Проверьте переменные окружения STRIPE_*_{currency.upper()}."
        )
    return keys


def _product_data(item: Item) -> dict:
    data = {"name": item.name}
    if item.description:
        data["description"] = item.description
    return data


def _sync_coupon(discount: Discount, secret_key: str) -> str:
    """Создаёт Stripe-купон при первом обращении и кэширует ID."""
    if discount.stripe_coupon_id:
        return discount.stripe_coupon_id
    kwargs = {"name": discount.name, "duration": "once"}
    if discount.percent_off:
        kwargs["percent_off"] = float(discount.percent_off)
    if discount.amount_off:
        kwargs["amount_off"] = int(discount.amount_off * 100)
        kwargs["currency"] = discount.currency
    coupon = stripe.Coupon.create(api_key=secret_key, **kwargs)
    discount.stripe_coupon_id = coupon.id
    discount.save(update_fields=["stripe_coupon_id"])
    return coupon.id


def _sync_tax(tax: Tax, secret_key: str) -> str:
    if tax.stripe_tax_rate_id:
        return tax.stripe_tax_rate_id
    tax_rate = stripe.TaxRate.create(
        api_key=secret_key,
        display_name=tax.name,
        percentage=float(tax.percentage),
        inclusive=tax.inclusive,
    )
    tax.stripe_tax_rate_id = tax_rate.id
    tax.save(update_fields=["stripe_tax_rate_id"])
    return tax_rate.id


def index(request):
    return render(request, "shop/index.html", {
        "items": Item.objects.all(),
        "orders": Order.objects.all(),
    })


@require_GET
def item_page(request, item_id):
    """HTML со страницей товара и кнопкой Buy."""
    item = get_object_or_404(Item, pk=item_id)
    keys = _stripe_keys(item.currency)
    return render(request, "shop/item.html", {
        "item": item,
        "publishable_key": keys["public"],
    })


@require_GET
def buy_item(request, item_id):
    """Создаёт Stripe Checkout Session и возвращает session.id."""
    item = get_object_or_404(Item, pk=item_id)
    keys = _stripe_keys(item.currency)

    session = stripe.checkout.Session.create(
        api_key=keys["secret"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": item.currency,
                "product_data": _product_data(item),
                "unit_amount": item.price_in_cents(),
            },
            "quantity": 1,
        }],
        success_url=request.build_absolute_uri("/success/"),
        cancel_url=request.build_absolute_uri(f"/item/{item.id}"),
    )
    return JsonResponse({"id": session.id})


@require_GET
def order_page(request, order_id):
    """HTML с содержимым заказа и кнопкой Pay."""
    order = get_object_or_404(Order, pk=order_id)
    currency = order.currency()
    keys = _stripe_keys(currency)
    return render(request, "shop/order.html", {
        "order": order,
        "publishable_key": keys["public"],
    })


@require_GET
def buy_order(request, order_id):
    """Создаёт Checkout Session на все Item в Order + скидка + налоги."""
    order = get_object_or_404(Order, pk=order_id)
    items = list(order.items.all())
    if not items:
        return HttpResponseBadRequest("Order has no items")

    currencies = {i.currency for i in items}
    if len(currencies) > 1:
        return HttpResponseBadRequest("Order contains items with different currencies")

    currency = items[0].currency
    keys = _stripe_keys(currency)

    tax_rate_ids = [_sync_tax(t, keys["secret"]) for t in order.taxes.all()]

    line_items = []
    for item in items:
        entry = {
            "price_data": {
                "currency": item.currency,
                "product_data": _product_data(item),
                "unit_amount": item.price_in_cents(),
            },
            "quantity": 1,
        }
        if tax_rate_ids:
            entry["tax_rates"] = tax_rate_ids
        line_items.append(entry)

    session_kwargs = dict(
        api_key=keys["secret"],
        mode="payment",
        line_items=line_items,
        success_url=request.build_absolute_uri("/success/"),
        cancel_url=request.build_absolute_uri(f"/order/{order.id}"),
    )

    if order.discount:
        coupon_id = _sync_coupon(order.discount, keys["secret"])
        session_kwargs["discounts"] = [{"coupon": coupon_id}]

    session = stripe.checkout.Session.create(**session_kwargs)
    return JsonResponse({"id": session.id})


@require_GET
def intent_item(request, item_id):
    """Возвращает client_secret для Stripe Elements."""
    item = get_object_or_404(Item, pk=item_id)
    keys = _stripe_keys(item.currency)
    intent = stripe.PaymentIntent.create(
        api_key=keys["secret"],
        amount=item.price_in_cents(),
        currency=item.currency,
        description=item.name,
        automatic_payment_methods={"enabled": True},
    )
    return JsonResponse({
        "client_secret": intent.client_secret,
        "publishable_key": keys["public"],
    })


@require_GET
def item_intent_page(request, item_id):
    """HTML с формой оплаты через PaymentIntent + Stripe Elements."""
    item = get_object_or_404(Item, pk=item_id)
    keys = _stripe_keys(item.currency)
    return render(request, "shop/item_intent.html", {
        "item": item,
        "publishable_key": keys["public"],
    })


def success(request):
    return HttpResponse(
        "<!doctype html><meta charset='utf-8'>"
        "<h1>Оплата прошла успешно</h1>"
        "<p>Спасибо! <a href='/'>Вернуться на главную</a></p>"
    )
