from django.db import models

class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="ID Telegram")
    username = models.CharField(max_length=255, null=True, blank=True, verbose_name="Имя пользователя")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Баланс")
    payment_details = models.CharField(max_length=100, null=True, blank=True, verbose_name="Реквизиты")

    def __str__(self):
        return f"{self.username} ({self.telegram_id})"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    article = models.CharField(max_length=50, default="", blank=True, verbose_name="Артикул WB")
    wb_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Цена на WB")
    cashback_percent = models.IntegerField(default=100, verbose_name="% Кэшбэка")
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Обложка товара")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена (в боте)")
    cashback = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Кэшбэк (фиксир.)")
    description = models.TextField(blank=True, default='', verbose_name="Описание")
    active = models.BooleanField(default=True, verbose_name="Активен")
    is_archived = models.BooleanField(default=False, verbose_name="В архиве")

    @property
    def calculated_cashback(self):
        return int(self.wb_price * self.cashback_percent / 100)

    def __str__(self):
        return f"{self.name} (Арт: {self.article})"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/', verbose_name="Фото")
    class Meta: verbose_name = "Фото галереи"; verbose_name_plural = "Галерея (Доп. фото)"

class Order(models.Model):
    STATUS_CHOICES = [
        ('ordered', 'Заказан (Ждет фото)'),
        ('check_wait', 'Ждет чек'),
        ('number_wait', 'Ждет номер чека'), # НОВЫЙ СТАТУС
        ('received', 'Получен (На проверке)'),
        ('approved', 'Выплачено (Архив)'),
        ('rejected', 'Отклонено'),
    ]

    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered', verbose_name="Статус")
    
    screenshot = models.ImageField(upload_to='proofs/', null=True, blank=True, verbose_name="Скрин ЛК")
    receipt_screenshot = models.ImageField(upload_to='checks/', null=True, blank=True, verbose_name="Скрин Чека")
    
    # НОВОЕ ПОЛЕ: Номер чека (цифры)
    check_number = models.CharField(max_length=255, blank=True, null=True, verbose_name="Номер с чека")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    is_archived = models.BooleanField(default=False, verbose_name="В архиве")

    def __str__(self):
        return f"Заказ #{self.id} - {self.user.username}"

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [('pending', 'Ожидает'), ('paid', 'Выплачено'), ('rejected', 'Отклонено')]
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, verbose_name="Пользователь")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    phone_number = models.CharField(max_length=50, verbose_name="Реквизиты")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    class Meta: verbose_name = "Заявка на вывод"; verbose_name_plural = "Заявки на вывод"

class CartItem(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('user', 'product'); verbose_name = "Товар в корзине"; verbose_name_plural = "Корзины пользователей"