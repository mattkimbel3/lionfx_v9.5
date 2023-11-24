# models.py

from django.db import models
from django.contrib.auth.models import User
from jsonfield import JSONField
from django.utils import timezone

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('DEMO', 'Demo Account'),
        ('LIVE', 'Live Account'),
        ('WALLET', 'Wallet Account'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_type = models.CharField(max_length=7, choices=ACCOUNT_TYPES, default='DEMO')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Specific to Live Account Models
    account_id = models.CharField(max_length=50, null=True, blank=True)
    currency = models.CharField(max_length=15, null=True, blank=True)
    leverage = models.CharField(max_length=15, null=True, blank=True)

    # Add any other account-related fields here
    def __str__(self):
        return f"{self.user.username} - {self.get_account_type_display()} Account"


class Profile(models.Model):
    username = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=10, null=True, blank=True)
    last_name = models.CharField(max_length=10, null=True, blank=True)
    user_id = models.PositiveSmallIntegerField(null=True, blank=True)

    country = models.CharField(max_length=10, null=True, blank=True)
    city = models.CharField(max_length=10, null=True, blank=True)
    zip_code = models.PositiveSmallIntegerField(null=True, blank=True)
    mobile_no = models.CharField(max_length=10, null=True, blank=True)
    address = models.CharField(max_length=30, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    dob = models.CharField(max_length=10, null=True, blank=True)
    about = models.CharField(max_length=200, null=True, blank=True)
    verification_status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ForexPair(models.Model):
    symbol = models.CharField(max_length=10, null=True, blank=True, default="LIONTC")
    pair = models.CharField(max_length=100, null=True, blank=True)
    chart_data = JSONField(default=list, null=True, blank=True)
    candle_chart_data = JSONField(default=list, null=True, blank=True)
    image = models.ImageField(default=False)

    def __str__(self):
        return self.symbol

class BitcoinWallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    private_key = models.CharField(max_length=100, null=True, blank=True)
    public_key = models.CharField(max_length=200, null=True, blank=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user} bitcoin wallet"

class CryptoPair(models.Model):
    symbol = models.CharField(max_length=10, null=True, blank=True, default="BTCUSD")
    pair = models.CharField(max_length=100, null=True, blank=True)
    chart_data = JSONField(default=list, null=True, blank=True)
    candle_chart_data = JSONField(default=list, null=True, blank=True)
    image = models.ImageField(default=False)

    def __str__(self):
        return self.symbol

class OptionTrade(models.Model):
    ASSET_CHOICES = [('FOREX', 'Forex'), ('CRYPTO', 'Crypto')]
    trader = models.ForeignKey(Account, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    stake = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expiration = models.PositiveSmallIntegerField()
    assets_type = models.CharField(max_length=10, choices=ASSET_CHOICES, default='FOREX')
    option_type = models.CharField(max_length=4)
    strike_price = models.DecimalField(max_digits=10, decimal_places=2)
    closing_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    outcome = models.CharField(max_length=4, null=True, blank=True)
    expire_time = models.PositiveSmallIntegerField(default=0)
    countdown = models.CharField(max_length=10, null=True, blank=True)  # Adjust minutes as needed
    time_now = models.DateTimeField(auto_now=True)
    close_time = models.DateTimeField(null=True, blank=True)  # Use PositiveIntegerField for Unix timestamps
    open_time = models.DateTimeField(null=True, blank=True)
    expired = models.BooleanField(default=False)

    def calculate_outcome(self):
        if self.option_type == 'CALL':
            if self.closing_price > self.strike_price:
                return 'won'
            else:
                return 'lost'
        elif self.option_type == 'PUT':
            if self.closing_price < self.strike_price:
                return 'won'
            else:
                return 'lost'

class Trade(models.Model):
    DIRECTION_CHOICES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    ASSET_CHOICES = [('FOREX', 'Forex'), ('CRYPTO', 'Crypto')]
    icon = models.ImageField(default=False)
    trader = models.ForeignKey(Account, on_delete=models.CASCADE)
    trade_direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES)
    assets_type = models.CharField(max_length=10, choices=ASSET_CHOICES, default='FOREX')
    entry = models.DecimalField(max_digits=10, decimal_places=5, default=False)
    take_profit = models.DecimalField(max_digits=10, decimal_places=5)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=5)
    lot_size = models.DecimalField(max_digits=10, decimal_places=2)
    equity = models.DecimalField(max_digits=10, decimal_places=2, default=False)
    symbol = models.CharField(max_length=7)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def close_trade(self):
        self.closed_at = timezone.now()
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.trade_direction} {self.lot_size} lots of {self.symbol}"

class Transaction(models.Model):
    trader = models.ForeignKey(Account, on_delete=models.CASCADE)
    description = models.CharField(max_length=100, null=True, blank=True) 
    transaction_id = models.PositiveSmallIntegerField(null=True, blank=True) # reference id
    amount = models.CharField(max_length=10)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)