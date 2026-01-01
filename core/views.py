import json
import requests
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, TelegramUser, Order, CartItem

BOT_TOKEN = os.getenv('BOT_TOKEN')

def webapp_catalog(request):
    user_id = request.GET.get('user_id')
    user = None
    orders = []
    bought_ids = []

    if user_id:
        try:
            user = TelegramUser.objects.get(telegram_id=user_id)
            orders = Order.objects.select_related('product').filter(user=user).order_by('-created_at')
            bought_ids = list(orders.values_list('product_id', flat=True))
        except TelegramUser.DoesNotExist: pass

    # ВАЖНО: Добавили prefetch_related('images') для загрузки галереи
    products = Product.objects.filter(active=True).prefetch_related('images')
    
    return render(request, 'core/catalog.html', {
        'products': products,
        'user': user,
        'orders': orders,
        'bought_ids': bought_ids
    })

# ... ОСТАЛЬНЫЕ ФУНКЦИИ (API) ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ КАК БЫЛИ ...
@csrf_exempt
def create_order_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            product_ids_str = data.get('products')
            if not user_id or not product_ids_str: return JsonResponse({'success': False, 'error': 'Нет данных'})
            try: user = TelegramUser.objects.get(telegram_id=user_id)
            except TelegramUser.DoesNotExist: return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
            p_ids = product_ids_str.split(',')
            count = 0
            product_names = []
            for pid in p_ids:
                if not pid: continue
                product = Product.objects.filter(id=int(pid)).first()
                if product:
                    if not Order.objects.filter(user=user, product=product).exists():
                        Order.objects.create(user=user, product=product, status='ordered')
                        count += 1
                        product_names.append(product.name)
            if count > 0:
                CartItem.objects.filter(user=user).delete()
                msg_text = f"✅ <b>Заказ принят!</b> ({count} шт.)\n\n" + "\n".join([f"• {n}" for n in product_names]) + "\n\nЖдите проверки!"
                send_telegram_message(user_id, msg_text)
                return JsonResponse({'success': True, 'message': 'Заказ создан'})
            else:
                send_telegram_message(user_id, "⚠️ Эти товары уже были заказаны.")
                return JsonResponse({'success': True, 'message': 'Дубликаты'})
        except Exception as e: return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

def get_cart_api(request):
    user_id = request.GET.get('user_id')
    if not user_id: return JsonResponse({'cart': []})
    try:
        user = TelegramUser.objects.get(telegram_id=user_id)
        cart_items = user.cart_items.select_related('product').all()
        cart_data = []
        for item in cart_items:
            p = item.product
            cart_data.append({
                'id': str(p.id),
                'name': p.name,
                'price': str(p.price),
                'img': p.image.url if p.image else ""
            })
        return JsonResponse({'cart': cart_data, 'payment_details': user.payment_details or "" })
    except: return JsonResponse({'cart': []})

@csrf_exempt
def update_cart_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        product_id = data.get('product_id')
        action = data.get('action')
        if not user_id or not product_id: return JsonResponse({'ok': False})
        user, _ = TelegramUser.objects.get_or_create(telegram_id=user_id)
        product = Product.objects.get(id=product_id)
        if action == 'add': CartItem.objects.get_or_create(user=user, product=product)
        elif action == 'remove': CartItem.objects.filter(user=user, product=product).delete()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})

@csrf_exempt
def save_payment_details_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        details = data.get('details')
        try:
            user = TelegramUser.objects.get(telegram_id=user_id)
            user.payment_details = details
            user.save()
            return JsonResponse({'ok': True})
        except: pass
    return JsonResponse({'ok': False})

def send_telegram_message(chat_id, text):
    if not BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    try: requests.post(url, json=payload, timeout=2)
    except: pass