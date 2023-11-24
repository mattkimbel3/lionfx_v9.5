from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Account, Trade, OptionTrade, CryptoPair, Profile, BitcoinWallet, Transaction

# Register your models here...
# (Your existing code for registering other models)

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0  # Setting extra to 0 will display existing transactions without an option to add new ones

class AccountAdmin(admin.ModelAdmin):
    inlines = [TransactionInline]
    list_display = ('user', 'balance', 'account_type', 'account_id')

admin.site.register(Account, AccountAdmin)
admin.site.register(BitcoinWallet)
admin.site.register(CryptoPair)
admin.site.register(OptionTrade)
admin.site.register(Trade)
admin.site.register(Profile)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'get_trader', 'amount', 'balance', 'date') 

    def get_trader(self, obj):
        return obj.trader.user.username  # Assuming the Account model has a user field
    get_trader.short_description = 'Account User'



admin.site.register(Transaction, TransactionAdmin)
