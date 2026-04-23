# Stripe × Django

Django-бэкенд на тестовое задание: модель `Item`, `GET /item/<id>` отдаёт HTML с кнопкой Buy, `GET /buy/<id>` создаёт `stripe.checkout.Session` и возвращает его id. JS на странице делает `stripe.redirectToCheckout`.

## Запуск

Нужны Stripe test-ключи: https://dashboard.stripe.com/test/apikeys

```bash
git clone <repo-url> && cd stripe-test
cp .env.example .env
docker compose up --build
```

Открыть http://localhost:8000, создать админа:

```bash
docker compose exec web python manage.py createsuperuser
```

<details>
<summary>Без Docker</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
</details>

## Как проверить

1. `/admin/` → создать `Item` (например: *Coffee*, price=`5.00`, currency=`usd`)
2. `/item/1` → кнопка **Buy** → редирект на Stripe Checkout
3. Тестовая карта: `4242 4242 4242 4242`, срок — любой будущий, CVC — любые 3 цифры

## Endpoints

| URL | Что отдаёт |
|---|---|
| `GET /item/<id>` | HTML товара + кнопка Buy |
| `GET /buy/<id>` | `{"id": "<stripe_session_id>"}` |
| `GET /order/<id>` | HTML заказа (несколько Item) |
| `GET /buy-order/<id>` | Checkout Session на весь Order + скидка/налоги |
| `GET /intent/<id>` | `{"client_secret", "publishable_key"}` для PaymentIntent |
| `GET /item-intent/<id>` | Форма оплаты на Stripe Elements |
| `GET /admin/` | Django admin |

## Env vars

Полный список — в `.env.example`.

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `STRIPE_PUBLIC_KEY_USD` / `STRIPE_SECRET_KEY_USD` — ключи для товаров в USD
- `STRIPE_PUBLIC_KEY_EUR` / `STRIPE_SECRET_KEY_EUR` — ключи для товаров в EUR

По `Item.currency` бэкенд сам берёт нужную пару. Если второго Stripe-аккаунта нет — можно подставить ту же пару в оба набора, всё будет работать.

## Что сделано из бонусов

- [x] Docker + docker-compose
- [x] Конфиг через env vars
- [x] Django admin для всех моделей
- [x] `Order` c несколькими `Item` и общей суммой через Stripe `line_items`
- [x] `Discount` → Stripe Coupon, `Tax` → Stripe TaxRate; создаются в Stripe лениво при первом использовании и кэшируются
- [x] `Item.currency` + 2 пары Stripe-ключей, выбор по валюте товара
- [x] `PaymentIntent` — `/intent/<id>` и `/item-intent/<id>` со Stripe Elements
- [ ] Удалённый сервер — не разворачивал, запуск локальный

## Стек

Django 4.2 · Python 3.10+ · `stripe` SDK · SQLite
