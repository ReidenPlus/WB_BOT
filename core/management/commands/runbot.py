from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command as TelegramCommand
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from core.models import TelegramUser, Order
import asyncio
import os
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
BASE_WEBAPP_URL = "*******" 

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def start_handler(message: types.Message):
    await TelegramUser.objects.aget_or_create(
        telegram_id=message.from_user.id, 
        defaults={'username': message.from_user.username}
    )
    personal_url = f"{BASE_WEBAPP_URL}?user_id={message.from_user.id}"
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Открыть Магазин", web_app=WebAppInfo(url=personal_url))]], 
        resize_keyboard=True
    )
    await message.answer("Добро пожаловать! Нажмите кнопку ниже.", reply_markup=kb)

async def text_handler(message: types.Message):
    if message.text.startswith('/'): return

    user = await TelegramUser.objects.aget(telegram_id=message.from_user.id)
    
    order = await Order.objects.filter(user=user, status='number_wait').select_related('product').alast()
    
    if order:
        order.check_number = message.text
        order.status = 'received' 
        await order.asave()
        
        await message.answer(
            f"✅ Данные приняты! Заказ на товар <b>{order.product.name}</b> отправлен на проверку.", 
            parse_mode="HTML"
        )

async def photo_handler(message: types.Message):
    user = await TelegramUser.objects.aget(telegram_id=message.from_user.id)
    
    order_waiting_check = await Order.objects.filter(user=user, status='check_wait').alast()
    order_new = await Order.objects.filter(user=user, status='ordered').alast()

    if not order_waiting_check and not order_new:
        await message.answer("⚠️ Нет активных заказов для загрузки фото.")
        return

    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)

    if order_waiting_check:
        path = f"checks/{user.telegram_id}_{order_waiting_check.id}_check.jpg"
        full_path = os.path.join(settings.MEDIA_ROOT, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        await bot.download_file(file.file_path, full_path)
        
        order_waiting_check.receipt_screenshot = path
        order_waiting_check.status = 'number_wait'
        await order_waiting_check.asave()
        
        await message.answer(
            f"🧾 Чек получен!\n\nТеперь отправьте <b>НОМЕР ЗАКАЗА или ЧЕКА</b> (цифры) текстом.", 
            parse_mode="HTML"
        )

    elif order_new:
        path = f"proofs/{user.telegram_id}_{order_new.id}.jpg"
        full_path = os.path.join(settings.MEDIA_ROOT, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        await bot.download_file(file.file_path, full_path)
        
        order_new.screenshot = path
        order_new.status = 'check_wait'
        await order_new.asave()
        
        await message.answer(
            f"📸 Скрин заказа принят! \nТеперь отправьте <b>СКРИНШОТ ЧЕКА</b>.", 
            parse_mode="HTML"
        )


class Command(BaseCommand):
    help = 'Run Bot'

    def handle(self, *args, **kwargs):
        if not TOKEN:
            print("ОШИБКА: Токен не найден в .env!")
            return
            
        dp.message.register(start_handler, TelegramCommand("start"))
        dp.message.register(text_handler, F.text)
        dp.message.register(photo_handler, F.photo)

        print("Бот запущен и оптимизирован...")
        asyncio.run(dp.start_polling(bot))
