"""lionfx URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from forex import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('trading/<str:account>/', views.TradingView, name='trading'),
    path('options_trading/<str:symbol>/<str:account>/', views.options, name='options'), 
    path('chartpage/', views.chartpage, name='chartpage'),
    path('add_funds/<str:account>/', views.add_funds, name='add_funds'),
    path('contest/<str:account>/', views.contest, name='contest'),
    path('withdraw_funds/<str:account>/', views.withdraw_funds, name='withdraw_funds'),
    path('notification/<str:account>/', views.notification, name='notification'),
    path('trader_profile/<str:account>/', views.trader_profile, name='trader_profile'),
    path('dashboard/<str:account>/', views.dashboard, name='dashboard'),
    path('statements/<str:account>/', views.account_statement, name='statments'),
    # path('candle_options/<str:symbol>/<str:account>/', views.candle_options, name='candle_options'),
    path('trade_options/<str:option_type>/<str:account>/', views.place_option_trade, name='place_option_trade'),
    path('trade_option/<str:option_type>/', views.place_candleoption_trade, name='place_candleoption_trade'),
    path('update_trade_outcomes/', views.update_trade_outcomes, name='update_trade_outcomes'),
    path('update_new_data/<str:account>/', views.update_new_data, name='update_new_data'),
    path('crypto/<str:symbol>/<str:account>/', views.cryptocurrency_trading, name='crypto'),
    path('update_chart_data/<str:symbol>/', views.update_chart_data, name='update_chart_data'),
    path('get_crypto_price/', views.get_crypto_price, name='get_crypto_price'),
    path('connect_wallet/', views.connect_wallet, name='connect_wallet'),
    path('wallet/<str:account>/', views.wallet, name='wallet'),
    path('deposit_eth/<str:account>/', views.deposit_eth, name='deposit_eth'),
    path('deposit_usdt/<str:account>/', views.deposit_usdt, name='deposit_usdt'),
    path('deposit_usdc/<str:account>/', views.deposit_usdc, name='deposit_usdc'),
    path('about_us/', views.about_us, name='about_us'),
    path('all_trades/<str:account>/', views.all_trades, name='all_trades'),
    path('confirm_email/', views.confirm_email, name='confirm_email'),
    path('privacy_policy/', views.privacy_policy, name='privacy_policy'),
    path('user_agreement/', views.user_agreement, name='user_agreement'),
    path('support/', views.support, name='support'),
    path('get_btc_historical_data/<str:symbol>/', views.get_btc_historical_data, name='get_btc_historical_data'),
    path('get_crypto_chart_data/<str:symbol>/', views.get_crypto_chart_data, name='get_crypto_chart_data'),
    path('get_polygon_forex_data/<str:symbol>/', views.get_polygon_forex_data, name='get_polygon_forex_data'), 
    path('get_forex_historical_data/<str:symbol>/', views.get_forex_historical_data, name='get_forex_historical_data'), 
    path('get_crypto_historical_line/<str:symbol>/', views.get_crypto_historical_line, name='get_crypto_historical_line'), 
    path('get_currencybeacon_forex_data/<str:symbol>/', views.get_currencybeacon_forex_data, name='get_currencybeacon_forex_data'),
    path('get_tiingo_forex_data/<str:symbol>/', views.get_tiingo_forex_data, name='get_tiingo_forex_data'), 
    path('get_forex_line_daily_data/<str:symbol>/', views.get_forex_line_daily_data, name='get_forex_line_daily_data'), 
    path('markers_chart/', views.markers_chart, name='markers_chart'),
    path('get_euro_usd_line/<str:symbol>/', views.get_euro_usd_line, name='get_euro_usd_line'),
    path('get_ticks_history/', views.get_ticks_history, name='get_ticks_history'),
    path('get_euro_usd_data/<str:symbol>/', views.get_euro_usd_data, name='get_euro_usd_data'),
    path('get_cap_historical_data/<str:symbol>/', views.get_cap_historical_data, name='get_cap_historical_data'),
    path('pair/<str:currency_pair>/<str:account>/', views.selected_pair, name='selected_pair'),
    path('crypto_pair/<str:currency_pair>/<str:account>/', views.crypto_selected_pair, name='crypto_selected_pair'),
    path('place_crypto_trade/<str:direction>/<str:account>/', views.place_crypto_trade, name='place_crypto_trade'),
    path('deposit/', views.deposit, name='deposit'),
    path('live_account/', views.open_live_account, name='open_live_account'),
    path('account_type/', views.account_type, name='account_type'),
    path('place_trade/<str:direction>/<str:account>/', views.place_trade, name='place_trade'),
    path('accounts/login/', views.login, name='login'),
    path('accounts/logout/', views.logout, name='logout'),
    path('accounts/signup/', views.register, name='sign_up')
]
