from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),


    path("item/<int:item_id>", views.item_page, name="item-page"),
    path("buy/<int:item_id>", views.buy_item, name="buy-item"),


    path("order/<int:order_id>", views.order_page, name="order-page"),
    path("buy-order/<int:order_id>", views.buy_order, name="buy-order"),

    path("intent/<int:item_id>", views.intent_item, name="intent-item"),
    path("item-intent/<int:item_id>", views.item_intent_page, name="item-intent-page"),

    path("success/", views.success, name="success"),
]
