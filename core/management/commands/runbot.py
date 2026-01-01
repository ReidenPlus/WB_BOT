from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command as TelegramCommand
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from core.models import TelegramUser, Product, Order, WithdrawalRequest
import asyncio
import os
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
BASE_WEBAPP_URL = "http://31.128.42.98:8000/webapp/"

class Command(BaseCommand):
    help = 'Run Bot'
    def handle(self, *args, **kwargs):
        if not TOKEN: print("ОШИБКА: Токен не найден!"); return
        asyncio.run(self.run_bot())

    async def run_bot(self):
        bot = Bot(token=TOKEN)
        dp = Dispatcher()

        @dp.message(TelegramCommand("start"))
        async def start(message: types.Message):
            await TelegramUser.objects.aget_or_create(
                telegram_id=message.from_user.id, 
                defaults={'username': message.from_user.username}
            )
            personal_url = f"{BASE_WEBAPP_URL}?user_id={message.from_user.id}"
            kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Открыть Магазин", web_app=WebAppInfo(url=personal_url))]], resize_keyboard=True)
            await message.answer("Добро пожаловать! Нажмите кнопку ниже.", reply_markup=kb)

        # ОБРАБОТЧИК ТЕКСТА (ДЛЯ НОМЕРА ЧЕКА)
        @dp.message(F.text)
        async def text_handler(message: types.Message):
            # Игнорируем команды типа /start
            if message.text.startswith('/'): return

            user = await TelegramUser.objects.aget(telegram_id=message.from_user.id)
            # Ищем заказ, который ждет ввода номера
            order = await Order.objects.filter(user=user, status='number_wait').alast()
            
            if order:
                # Сохраняем введенный текст как номер чека
                order.check_number = message.text
                order.status = 'received' # Переводим на финальную проверку
                await order.asave()
                
                await message.answer(f"✅ Данные приняты! Заказ на товар <b>{order.product.name}</b> отправлен на проверку администратору.", parse_mode="HTML")
            else:
                # Если человек просто пишет текст, а мы ничего не ждем
                pass

        # ОБРАБОТЧИК ФОТО
        @dp.message(F.photo)
        async def photo_handler(message: types.Message):
            user = await TelegramUser.objects.aget(telegram_id=message.from_user.id)
            
            order_waiting_check = await Order.objects.filter(user=user, status='check_wait').alast()
            order_new = await Order.objects.filter(user=user, status='ordered').alast()

            file_id = message.photo[-1].file_id
            file = await bot.get_file(file_id)

            if order_waiting_check:
                # ЭТО ВТОРОЙ СКРИН (ЧЕК)
                path = f"checks/{user.telegram_id}_{order_waiting_check.id}_check.jpg"
                full_path = os.path.join(settings.MEDIA_ROOT, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                await bot.download_file(file.file_path, full_path)
                
                order_waiting_check.receipt_screenshot = path
                order_waiting_check.status = 'number_wait' # ТЕПЕРЬ ЖДЕМ ЦИФРЫ
                await order_waiting_check.asave()
                
                await message.answer(f"🧾 Чек получен!\n\nТеперь отправьте <b>НОМЕР ЗАКАЗА или ЧЕКА</b> (цифры) текстом в этот чат для подтверждения.", parse_mode="HTML")

            elif order_new:
                # ЭТО ПЕРВЫЙ СКРИН (ЛК)
                path = f"proofs/{user.telegram_id}_{order_new.id}.jpg"
                full_path = os.path.join(settings.MEDIA_ROOT, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                await bot.download_file(file.file_path, full_path)
                
                order_new.screenshot = path
                order_new.status = 'check_wait'
                await order_new.asave()
                
                await message.answer(f"📸 Скрин заказа принят! \nТеперь отправьте <b>СКРИНШОТ ЧЕКА</b>.", parse_mode="HTML")
            else:
                await message.answer("⚠️ Нет активных заказов для фото.")

        print("Бот запущен...")
        await dp.start_polling(bot)