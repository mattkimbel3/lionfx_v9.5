import requests
from django.shortcuts import render
from django.contrib.auth.models import User, auth
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from bs4 import BeautifulSoup   
from django.contrib.auth.decorators import login_required
from .models import Account, Trade, ForexPair, OptionTrade, CryptoPair, Profile, BitcoinWallet, Transaction
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from lxml import etree
import http.client
import decimal
from bitcoin import *
from decimal import Decimal
from django.views.generic import View
import json
from django.core import serializers
import random
import subprocess
import web3
from web3 import Web3, HTTPProvider
import uuid
import time  # Import the time module
import datetime
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, HttpResponseServerError
from django.core.mail import send_mail
from random import uniform
import yfinance as yf


# Authentication Views

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('home')
        else:
            messages.info(request, 'Invalid Credentials')
            return redirect('login')

    else:
        return render(request, 'login.html')

def register(request):

    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        demo_account_id = '0001' + str(random.randint(10000000000, 99999999999))
        account_id = '65' + str(random.randint(10000000000, 99999999999))
        if password==password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email Taken, Please Choose a diffrent Email.')
                return redirect(reverse('sign_up')) # redirect to the sign up page using the reverse function
            elif User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken, Please choose a diffrent username.')
                return redirect(reverse('sign_up')) # redirect to the sign up page using the reverse function
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                demo_account = Account.objects.create(user=user, balance=1000.00, account_type='DEMO', account_id=demo_account_id)
                demo_account.save()

                live_account = Account.objects.create(user=user, balance=0.00, account_type='LIVE', account_id=account_id)
                live_account.save()

                profile = Profile.objects.create(username=user, user_id=account_id)
                profile.save()

                # User does not have a wallet, create new one
                private_key = random_key()
                public_key = privtopub(private_key)
                address = pubtoaddr(public_key)
                print(f"Bitcoin Address: {address}")

                api_url = f'https://blockchain.info/rawaddr/{address}'
                response = requests.get(api_url)
                wallet_data = response.json()

                balance = wallet_data['final_balance'] / 100000000

                wallet = BitcoinWallet.objects.create(
                    user=user,
                    address=address,
                    private_key=private_key,
                    public_key=public_key,
                    balance=balance
                )

                wallet_account = Account.objects.create(user=user, balance=balance, account_type='WALLET', account_id=address)
                wallet_account.save()

                
                print('User Created')
                return redirect('login')

        else:
            messages.info(request, 'Password Not Matching')
            return redirect(reverse('sign_up'))  # redirect to the sign up page using the reverse function
        return redirect('/')

    else:
        return render(request, 'register.html')

def logout(request):
    auth.logout(request)
    return redirect('/')

# ... after processing the form data ...

# Project  views.

def index(request):
    user = request.user
    if request.method == 'POST':
        email = request.POST['email']

        # # Send welcome email
        # send_mail(
        #     'Welcome!', 
        #     'Thanks for confirming your email. Click here to continue your registration!',
        #     'from@example.com',
        #     [email],
        #     fail_silently=False
        # )

        return redirect('confirm_email')
    
    context = {'user': user}
    return render(request, 'index.html')

def confirm_email(request):
    user = request.user
    
    context = {'user': user}
    return render(request, 'confirm_email.html')

def get_forex_price(forex_pair):
    API_KEY = "e467de385980e930097f0386"  # Replace with your actual API key
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/pair/{forex_pair}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data.get("conversion_rate")
    else:
        print(f"Error: Failed to fetch {forex_pair} price. Status Code: {response.status_code}")
        return None

def get_trade_equity(trade):
    forex_pairs = CryptoPair.objects.all()
    # Find the ForexPair object with a matching symbol to the trade's symbol
    matched_pair = None
    for forex_pair in forex_pairs:
        if trade.symbol == forex_pair.symbol:
            matched_pair = forex_pair
            break
    
    if matched_pair is None:
        print(f"Error: Could not find matching ForexPair for symbol {trade.symbol}")
        return None
    
    # Get the current price using the matched pair's pair
    chart = matched_pair.candle_chart_data
    latest_point = chart[-1]
    current_price = latest_point['close']
    current_price_decimal = Decimal(str(current_price))  # Convert to Decimal

    if current_price_decimal is not None:
        entry_price = Decimal(str(trade.entry))  # Convert to Decimal
        direction = trade.trade_direction
        lot_size = trade.lot_size
        
        if direction == 'BUY':
            equity = (current_price_decimal - entry_price) * lot_size * 1000
        elif direction == 'SELL':
            equity = (entry_price - current_price_decimal) * lot_size * 1000
        else:
            print(f"Error: Invalid trade direction {direction}")
            return None
        
        return equity
    else:
        print(f"Error: Could not fetch current price for {trade.symbol}")
        return None


def get_alpha_vantage_price(forex_pair):
    api_key = "5GYXW0UKZYXGSPAT"
    
    # Split the forex_pair into from_currency and to_currency
    from_currency, to_currency = forex_pair.split('/')
    
    # Construct the Alpha Vantage API URL for forex data
    base_url = "https://www.alphavantage.co/query"
    function = "CURRENCY_EXCHANGE_RATE"
    
    # Build the API request URL
    params = {
        "function": function,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "apikey": api_key,
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if "Realtime Currency Exchange Rate" in data:
            exchange_rate = float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
            print(f"Exchange rate for {from_currency}/{to_currency} is {exchange_rate}")
            return exchange_rate
        else:
            print(f"Error fetching {forex_pair} price from Alpha Vantage API")
            return None

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def get_forex_line_daily_data(request, symbol):
    
    api_key = "8ce4db817f206edbf7ec8277d4813ef33e89e8f4f0dbec18cf4df57457983fe5"
    
    # Split the forex_pair into from_currency and to_currency
    from_currency = symbol[:3]
    print(f"Historical Data Symbol {symbol}")
    to_currency = symbol[3:]
    pair = ForexPair.objects.get(symbol=symbol)
    
    # Construct the Alpha Vantage API URL for forex data
    base_url = "https://www.alphavantage.co/query"
    function = "FX_DAILY"
    
    # Build the API request URL
    params = {
        "function": function,
        "from_symbol": from_currency,
        "to_symbol": to_currency,
        "outputsize": "full",
        "apikey": api_key,
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if "Time Series FX (Daily)" in data:
            daily_data = data["Time Series FX (Daily)"]
            print(f"Daily data for {from_currency}/{to_currency}:")
        
            transformed_data = []
            for date, values in daily_data.items():
                transformed_data.append({
                    "time": date,
                    "value": float(values["4. close"])
                })
            pair.chart_data = transformed_data
            pair.save()
            
            return JsonResponse(transformed_data, safe=False)
        else:
            print(f"Error fetching {symbol} daily data from Alpha Vantage API")
            return HttpResponseServerError("An error occurred while fetching or processing data.")

    except Exception as e:
        print(f"Error: {str(e)}")
        return HttpResponseServerError("An error occurred while fetching or processing data.")

def get_cap_historical_data(request, symbol):
    try:
        # Calculate Unix timestamps
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - (365 * 24 * 60 * 60)  # One year ago

        # API params
        api_url = f"https://api.coincap.io/v2/assets/EURUSD/history"
        
        # Make request
        params = {
            "interval": "d1",
            "start": start_timestamp,
            "end": end_timestamp
        }

        response = requests.get(api_url, params)
        response.raise_for_status()  # Raise exception for HTTP errors

        response_data = response.json()

        if "data" not in response_data:
            return HttpResponseServerError("No data found in the API response.")

        data = response_data["data"]

        # Transform data
        transformed_data = []
        for d in data:
            price = float(d.get("priceUsd", 0.0))
            formatted_price = "{:.4f}".format(price)

            transformed_data.append({
                "time": d.get("time", ""),
                "value": formatted_price
            })

        # Save to DB (ensure you have imported your ForexPair model)
        pair, created = ForexPair.objects.get_or_create(symbol=symbol)
        pair.chart_data = transformed_data
        pair.save()

        # Return JSON response
        return JsonResponse(transformed_data, safe=False)

    except requests.exceptions.RequestException as e:
        print("Error making API request:", e)
        return HttpResponseServerError("An error occurred while making the API request.")

    except Exception as e:
        print("Error fetching or processing data:", e)
        return HttpResponseServerError("An error occurred while fetching or processing data.")


@login_required
def TradingView(request, account):
    user = request.user
    forex_pairs = ForexPair.objects.all()

    forex_prices = {}
    trade_equity = {}
    total_equity = decimal.Decimal('0.0')
    trading_account = Account.objects.get(user=request.user, account_type=account)
    trades = Trade.objects.filter(trader=trading_account)
    symbol = 'EURUSD'
    get_euro_usd_data(request, symbol)
    duka_historical_tick_data(request)

    for forex_pair in forex_pairs:

        pair_data = ForexPair.objects.get(pair=forex_pair.pair)

        if pair_data.chart_data:
            chart_data = pair_data.chart_data
            latest_point = chart_data[-1]
            price = latest_point['value']
        
        else:
            price = None

        if price:
            forex_prices[forex_pair] = price
            print(f"Pair: {forex_pair}, Price: {price}")

    for trade in trades:
        pair_symbol = trade.symbol

        for forex_pair in forex_pairs:
            if forex_pair.symbol == pair_symbol:
                matched_pair = forex_pair.pair
                print(f"Symbol found {matched_pair}")
            else:
                print(f"Symbol is not found.")

        if matched_pair:
            pair_data = ForexPair.objects.get(pair=forex_pair.pair)

            if pair_data.chart_data:
                chart_data = pair_data.chart_data
                latest_point = chart_data[-1]
                price = latest_point['value']
            
            else:
                price = None

            if price:
                current_price = price

            if current_price:
                equity = get_trade_equity(trade)
                trade_equity[trade] = equity
                total_equity += equity  # Add the equity to total equity
                trade.equity = equity
                trade.save()
                print(f"Trade {trade}, Equity {trade_equity[trade]}")
            else:
                print(f"No price found for symbol {pair_symbol}")
        else:
            print(f"Symbol Not found for trade {trade}")


    # Get the user's demo account balance
    default_pair = ForexPair.objects.get(pair='EUR/USD')
    default_chart = default_pair.chart_data[-1]
    default_price = default_chart['value']
    print(f"Default price: {default_price}")
    
    trading_account_balance = trading_account.balance
    balance_equity = trading_account_balance + total_equity
    open_positions = []  # Retrieve user's open positions from the database
    transaction_history = []  # Retrieve user's transaction history from the database

    context = {
        'trades': trades,
        'trade_equity': trade_equity,
        'total_equity': total_equity,
        'balance_equity': balance_equity,
        'forex_prices': forex_prices,
        'default_price': default_price,
        'account_balance': trading_account_balance,
        'account': account,
        'open_positions': open_positions,
        'transaction_history': transaction_history,
        'user': user,
    }
    return render(request, 'trading.html', context)

def account_statement(request, account):
    user = request.user
    trading_account = Account.objects.get(user=user, account_type=account)
    transactions = Transaction.objects.filter(trader=trading_account).order_by('-id')[:10]

    print(f"statements {transactions}")
    # Transform format 
    chart_date = []
    chart_balance = []

    for transaction in transactions():
        dates.append(transaction.date) 
        balances.append(transaction.balance)
        
    print(f"Chart Date: {chart_date}")
    print(f"Chart Balance: {chart_balance}")
    context = {
        'user': user,
        'account': account,
        'transactions': transactions
    }

    return render(request, 'statements.html', context)

def account_type(request):
    return render(request, 'account_type.html')

def open_live_account(request):
    user = request.user
    account_id = '65' + str(random.randint(10000000000, 99999999999))

    COUNTRY_CHOICES = [
        ('US', 'United States'), 
        ('CA', 'Canada'), 
        ('AU', 'Australia'),
        ('AT', 'Austria'),
        ('BE', 'Belgium'),
        ('DK', 'Denmark'),
        ('FI', 'Finland'), 
        ('FR', 'France'),
        ('DE', 'Germany'),
        ('GR', 'Greece'),
        ('IS', 'Iceland'),
        ('IE', 'Ireland'),
        ('IT', 'Italy'),
        ('JP', 'Japan'),
        ('LU', 'Luxembourg'),
        ('NL', 'Netherlands'),
        ('NZ', 'New Zealand'),
        ('NO', 'Norway'),
        ('PT', 'Portugal'),
        ('ES', 'Spain'),
        ('SE', 'Sweden'),
        ('CH', 'Switzerland'),
        ('GB', 'United Kingdom'),
        ('BG', 'Bulgaria'),
        ('HR', 'Croatia'),
        ('CY', 'Cyprus'),
        ('CZ', 'Czechia'),
        ('EE', 'Estonia'),
        ('HU', 'Hungary'),
        ('LV', 'Latvia'),
        ('LT', 'Lithuania'),
        ('MT', 'Malta'),
        ('PL', 'Poland'),
        ('RO', 'Romania'),
        ('SK', 'Slovakia'),
        ('SI', 'Slovenia'),
        ('KR', 'South Korea'),
        ('SA', 'South Africa'),
        ('AR', 'Argentina'),
        ('CL', 'Chile'), 
        ('CN', 'China'),
        ('CO', 'Colombia'),
        ('CU', 'Cuba'),
        ('DO', 'Dominican Republic'), 
        ('EC', 'Ecuador'),
        ('SV', 'El Salvador'),
        ('GT', 'Guatemala'),
        ('ME', 'Montenegro'),
        ('MX', 'Mexico'),
        ('RS', 'Serbia'),
        ('UY', 'Uruguay'),
        ('VE', 'Venezuela'),
        ('BD', 'Bangladesh'),
        ('ET', 'Ethiopia'), 
        ('IN', 'India'),
        ('KE', 'Kenya'),
        ('MW', 'Malawi'),
        ('MZ', 'Mozambique'),
        ('NG', 'Nigeria'),
        ('NP', 'Nepal'),
        ('RW', 'Rwanda'),
        ('TZ', 'Tanzania'),
        ('UG', 'Uganda'),
        ('ZM', 'Zambia'),
        ('ZW', 'Zimbabwe'),
    ]

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        dob = request.POST['dob']
        country = request.POST['country']
        mobile_no = request.POST['mobile_no']
        currency = request.POST['currency']
        leverage = request.POST['leverage']

        # Save the trade details to the database
        account = Account.objects.create(
            user=user,
            account_type='LIVE',
            balance=0.00,
            currency=currency,
            leverage=leverage,
            account_id=account_id,
        )
        account.save()

        # Create profile object
        profile = Profile.objects.create(
            user_id=account_id,
            username=user,
            first_name=first_name,
            last_name=last_name,
            country=country,
            mobile_no=mobile_no,
            dob=dob,
        )
        profile.save()

        return redirect('deposit')
        
    context = {
        'COUNTRY_CHOICES': COUNTRY_CHOICES,

    }

    return render(request, 'open_live_account.html', context)

def deposit(request):
    return render(request, 'deposit.html')

def get_euro_usd_line(request, symbol):

    # Fetch 1 min bars 
    end = datetime.datetime.today() 
    start = end - datetime.timedelta(minutes=1000)
    eurusd = yf.Ticker(f"{symbol}=X")
    hist = eurusd.history(period=f"{start} {end}", interval="1m")

    # Get current price 
    current_price = eurusd.info['regularMarketPrice'] 

    pair = ForexPair.objects.get(symbol=symbol)
    
    # Transform format 
    transformed_data = []

    for index, row in hist.iterrows():
        timestamp = int(index.timestamp())

        item = {
            "time": timestamp,  
            "value": row["Close"]
        }
        
        transformed_data.append(item)

    pair.chart_data = transformed_data
    pair.save()

    return JsonResponse(transformed_data, safe=False)

def get_euro_usd_data(request, symbol):

    # Fetch 1 min bars 
    end = datetime.datetime.today() 
    start = end - datetime.timedelta(minutes=1000)
    eurusd = yf.Ticker(f"{symbol}=X")
    hist = eurusd.history(period=f"{start} {end}", interval="1m")

    # Get current price 
    current_price = eurusd.info['regularMarketPrice'] 

    pair = ForexPair.objects.get(symbol=symbol)
    
    # Transform format 
    transformed_data = []

    for index, row in hist.iterrows():
        timestamp = int(index.timestamp())

        item = {
            "time": timestamp,  
            "high": row["High"],
            "low": row["Low"], 
            "open": row["Open"],
            "close": row["Close"]
        }
        
        transformed_data.append(item)

    pair.candle_chart_data = transformed_data
    pair.save()

    return JsonResponse(transformed_data, safe=False)

def duka_historical_tick_data(request):
    # Define the symbol
    symbol = 'EURUSD'

    # Calculate the start and end times
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(hours=1)

    # Format the start and end times as strings
    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

    # Construct the duka command
    duka_command = f'duka {symbol} -s {start_time_str} -e {end_time_str}'

    try:
        # Run the duka command and capture its output
        result_bytes = subprocess.check_output(duka_command, shell=True, stderr=subprocess.STDOUT)

        # Decode the output to text
        result = result_bytes.decode('utf-8')

        # Assuming duka outputs data in a specific format, you can parse it as needed

        # For demonstration purposes, split the result into lines and format as JSON
        lines = result.split('\n')
        formatted_data = [{'time': line.split()[0], 'value': float(line.split()[1])} for line in lines]

        print(f"Data: {formatted_data}")

        return JsonResponse({'tick_data': formatted_data})
    except subprocess.CalledProcessError as e:
        print(f"Formatted data not found")
        return JsonResponse({'error': 'Error executing duka command', 'details': str(e)})


def get_eurusd_ticks(request):

    eurusd = yf.Ticker("EURUSD=X")

    # Generator object 
    ticks = eurusd.ticker()

    print("Ticks:")

    for tick in ticks:
        print(tick)

    # Stream ticks
    for tick in ticks:

        # Split string on commas
        time, price, volume = tick.split(',')  

        tick_data.append({
            "time": int(time),
            "price": row["Close"], 
        })

    print(f"Tick Data {tick_data}")

    return JsonResponse(tick_data, safe=False)

def get_ticks_history(request):
    # Replace with your actual app_id
    app_id = "Pf9Q9Hd2IOScnSN"

    # Define the API request parameters
    api_url = "https://api.deriv.com/api/tickhistory/R_50"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "ticks_history": "R_50",
        "adjust_start_time": 1,
        "count": 10,
        "end": "latest",  # You can replace this with a specific timestamp if needed
        "start": 1,  # Adjust as needed
        "style": "ticks",  # You can change this to "candles" if desired
        "subscribe": 1,  # Set to 1 to receive updates
        "app_id": app_id,
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        tick_data = response.json()

        # You can process the tick data as needed here
        print("Ticks Data:", tick_data)

        return JsonResponse(tick_data)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return JsonResponse({"error": "Failed to fetch tick data"}, status=500)

@login_required
def cryptocurrency_trading(request, symbol, account):
    user = request.user
    crypto_pairs = CryptoPair.objects.all()
    pairs = CryptoPair.objects.all()
    wallet = BitcoinWallet.objects.get(user=request.user)

    crypto_prices = {}
    trade_equity = {}
    
    total_equity = decimal.Decimal('0.0')
    
    trading_account = Account.objects.get(user=request.user, account_type=account)
    trades = Trade.objects.filter(trader=trading_account, assets_type='CRYPTO')
            
    for crypto_pair in crypto_pairs:

        pair_data = CryptoPair.objects.get(pair=crypto_pair.pair)

        if pair_data.candle_chart_data:
            chart_data = pair_data.candle_chart_data
            latest_point = chart_data[-1]
            price = latest_point['close']
        
        else:
            price = None

        if price:
            crypto_prices[crypto_pair] = price
            print(f"Pair: {crypto_pair}, Price: {price}")

    for trade in trades:
        pair_symbol = trade.symbol

        for crypto_pair in crypto_pairs:
            if crypto_pair.symbol == pair_symbol:
                matched_pair = crypto_pair
                print(f"Symbol found {matched_pair}")
            else:
                print(f"Symbol is not found.")

        if matched_pair:
            chart_data = matched_pair.candle_chart_data
            latest_point = chart_data[-1]
            current_price = latest_point['close']
            if current_price:
                equity = get_trade_equity(trade)
                trade_equity[trade] = equity
                total_equity += equity  # Add the equity to total equity
                trade.equity = equity
                trade.save()
                print(f"Trade {trade}, Equity {trade_equity[trade]}")
            else:
                print(f"No price found for symbol {pair_symbol}")
        else:
            print(f"Symbol Not found for trade {trade}")


    # Get the user's demo account balance
    default_pair = CryptoPair.objects.get(symbol='BTCUSD')
    default_chart = default_pair.candle_chart_data
    default_latest_point = default_chart[-1]
    default_price = default_latest_point['close']
    print(f"Default price: {default_price}")
    print(f"Crypto Symbol: {symbol}")
    trading_account_balance = trading_account.balance
    # Assuming trading_account is an instance of your model
    account_id = wallet.address

    # Extract first four and last six characters
    if len(account_id) >= 10:
        shortened_account_id = account_id[:5] + "..." + account_id[-6:]
    else:
        # Handle cases where account_id is too short
        shortened_account_id = account_id

    print(f"Account ID: {shortened_account_id}")
    balance_equity = trading_account_balance + total_equity
    open_positions = []  # Retrieve user's open positions from the database
    transaction_history = []  # Retrieve user's transaction history from the database

    context = {
        'trades': trades,
        'trade_equity': trade_equity,
        'total_equity': total_equity,
        'balance_equity': balance_equity,
        'forex_prices': crypto_prices,
        'pairs': pairs,
        'crypto_pairs': crypto_pairs,
        'account': account,
        'account_id': shortened_account_id,
        'symbol': symbol,
        'trading_account': trading_account,
        'default_price': default_price,
        'account_balance': trading_account_balance,
        'open_positions': open_positions,
        'transaction_history': transaction_history,
        'demo_account_balance': trading_account_balance,
        'user': user,
    }

    return render(request, 'dashboard/includes/trading_panel.html', context)

def wallet(request, account):

    user = request.user

    # Check if user already has a wallet
    try:
        wallet = BitcoinWallet.objects.get(user=user)

        address = wallet.address

        api_url = f'https://blockchain.info/rawaddr/{address}'
        response = requests.get(api_url)
        wallet_data = response.json()

        balance = wallet_data['final_balance'] / 100000000

        wallet.balance = balance
        wallet.save()
    
    except BitcoinWallet.DoesNotExist:
        # User does not have a wallet, create new one
        private_key = random_key()
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)
        print(f"Bitcoin Address: {address}")

        api_url = f'https://blockchain.info/rawaddr/{address}'
        response = requests.get(api_url)
        wallet_data = response.json()

        balance = wallet_data['final_balance'] / 100000000

        wallet = BitcoinWallet.objects.create(
        user=user,
        address=address,
        private_key=private_key,
        public_key=public_key,
        balance=balance
        )

        wallet_account = Account.objects.create(user=user, balance=balance, account_type='wallet', account_id=address)
        wallet_account.save()

    # Get wallet details
    api_url = f'https://blockchain.info/rawaddr/{wallet.address}'
    response = requests.get(api_url)
    
    wallet_data = response.json()
    print(f"Wallet Details: {wallet_data}")
    balance = wallet_data['final_balance'] / 100000000
    print(f"Wallet Balance: {balance}")

    context = {
        'address': wallet.address,
        'balance': balance,
        'account': account
    }

    return render(request, 'wallet.html', context)


def connect_wallet(request):
    # Connect to the Ethereum network
    web3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'))
    # Check if MetaMask is available
    if not web3.isConnected() or web3.eth.accounts[0] is None:
        return render(request, 'wallet_connect.html', {'error': 'MetaMask wallet not detected.'})

    # Retrieve the user's MetaMask account address
    account = web3.eth.accounts[0]
    print(f"Connected wallet address: {account}")

    # Pass the account address to your template or use it for further processing

    return render(request, 'wallet_connected.html', {'account': account})


@login_required
def options(request, symbol, account):
    user = request.user
    update_trade_outcomes(request)
    pair_prices = {}
    pairs = CryptoPair.objects.all()  # Default symbol
    print(f"Account {account}")
    wallet = BitcoinWallet.objects.get(user=request.user)
    trading_account = Account.objects.get(user=request.user, account_type=account)
    account_balance = trading_account.balance
    
    print(f"Account Number {trading_account}")
    get_crypto_chart_data(request, symbol)
    trades = OptionTrade.objects.filter(trader=trading_account, expired=False, assets_type='CRYPTO').order_by('-id')
    all_trades = OptionTrade.objects.filter(trader=trading_account, assets_type='CRYPTO').order_by('-id')
    closed_trades = OptionTrade.objects.filter(trader=trading_account, expired=True, assets_type='CRYPTO').order_by('-id')[:4]

    # Assuming trading_account is an instance of your model
    account_id = wallet.address

    # Extract first four and last six characters
    if len(account_id) >= 10:
        shortened_account_id = account_id[:4] + "..." + account_id[-6:]
    else:
        # Handle cases where account_id is too short
        shortened_account_id = account_id

    print(f"Account ID: {shortened_account_id}")

    try:
        forex_pair = CryptoPair.objects.get(symbol=symbol)
        chart_data = forex_pair.chart_data
        # print(f"Chart Data for {symbol} is {chart_data}")
        
    except CryptoPair.DoesNotExist:
        chart_data = []
    
    for pair in pairs:

        pair_data = CryptoPair.objects.get(pair=pair.pair)

        if pair_data.chart_data:
            chart_data = pair_data.chart_data
            latest_point = chart_data[-1]
            price = latest_point['value']
        
        else:
            price = None

        if price:
            pair_prices[pair] = price
            print(f"Pair: {pair}, Price: {price}")
    

    print(f"Symbol {symbol}")

    context = {
        'chart_data': json.dumps(chart_data),
        'pairs': pairs,
        'trades': trades,
        'account_id': shortened_account_id,
        'trading_account':trading_account,
        'all_trades': all_trades,
        'closed_trades': closed_trades,
        'account': account,
        'symbol': symbol,
        'demo_account_balance': account_balance
    }

    return render(request, 'options.html', context)

def about_us(request):
    return render(request, 'about_us.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_of_service(request):
    return render(request, 'terms_of_service.html')

def user_agreement(request):
    return render(request, 'user_agreement.html')


# @login_required
# def candle_options(request, symbol, account):
#     user = request.user
#     update_trade_outcomes(request)
#     pairs = CryptoPair.objects.all()  # Default symbol
#     print(f"Account {account}")
#     trading_account = Account.objects.get(user=request.user, account_type=account)
#     account_balance = trading_account.balance
#     print(f"Account Number {trading_account}")
#     get_crypto_historical_data(request, symbol)
#     trades = OptionTrade.objects.filter(trader=trading_account, expired=False, assets_type='CRYPTO').order_by('-id')
#     all_trades = OptionTrade.objects.filter(trader=trading_account, assets_type='CRYPTO').order_by('-id')
#     closed_trades = OptionTrade.objects.filter(trader=trading_account, expired=True, assets_type='CRYPTO').order_by('-id')[:5]

#     try:
#         forex_pair = CryptoPair.objects.get(symbol=symbol)
#         chart_data = forex_pair.candle_chart_data
#         # print(f"Chart Data for {symbol} is {chart_data}")
        
#     except CryptoPair.DoesNotExist:
#         chart_data = []
    
#     print(f"Symbol {symbol}")

#     context = {
#         'candle_data': json.dumps(chart_data),
#         'pairs': pairs,
#         'trades': trades,
#         'all_trades': all_trades,
#         'closed_trades': closed_trades,
#         'account': account,
#         'symbol': symbol,
#         'demo_account_balance': account_balance
#     }

#     return render(request, 'candle_options.html', context)

def get_btc_historical_data(request, symbol):
    pair = ForexPair.objects.get(symbol=symbol)
    # Fetch 1 min bars 
    end = datetime.datetime.today() 
    start = end - datetime.timedelta(minutes=10000)
    eurusd = yf.Ticker(f"{symbol}=X")
    hist = eurusd.history(period=f"{start} {end}", interval="1m")

    # Get current price 
    current_price = eurusd.info['regularMarketPrice'] 
    
    # Transform format 
    transformed_data = []

    for index, row in hist.iterrows():
        timestamp = int(index.timestamp())

        item = {
            "time": timestamp,  
            "high": row["High"],
            "low": row["Low"], 
            "open": row["Open"],
            "close": row["Close"]
        }
        
        transformed_data.append(item)
    
        pair.candle_chart_data = transformed_data
        pair.save()

        return JsonResponse(transformed_data, safe=False)
    else: 
        print("Error getting historical data")
    
    return None

def get_crypto_historical_data(request, symbol):
    from_currency = symbol[:3]
    print(f"Historical Data Symbol {symbol}")
    to_currency = symbol[3:]
    pair = CryptoPair.objects.get(symbol=symbol)
    start = int(datetime.datetime(2023, 1, 1).timestamp())
    end = int(datetime.datetime.now().timestamp())
    api_url = "https://min-api.cryptocompare.com/data"

    parameters = {
        "fsym": from_currency,
        "tsym": to_currency,
        "limit": 2000,
        "toTs": end,
        "aggregate": 1
    }

    response = requests.get(f"{api_url}/histoday", params=parameters)

    if response.status_code == 200:
        data = json.loads(response.text)
        transformed_data = []
        

        for d in data["Data"]:
            time_str = datetime.datetime.utcfromtimestamp(d["time"]).strftime("%Y-%m-%d %H:%M")
            transformed_data.append({
                "time": d["time"],
                "high": d["high"],
                "low": d["low"],
                "open": d["open"],
                "close": d["close"]
            })
        pair.candle_chart_data = transformed_data
        pair.save()

        return JsonResponse(transformed_data, safe=False)
    else: 
        print("Error getting historical data")
    
    return None

def get_crypto_historical_line(request, symbol):
    from_currency = symbol[:3]
    print(f"Historical Data Symbol {symbol}")
    to_currency = symbol[3:]
    pair = CryptoPair.objects.get(symbol=symbol)
    start = int(datetime.datetime(2023, 1, 1).timestamp())
    end = int(datetime.datetime.now().timestamp())
    api_url = "https://min-api.cryptocompare.com/data"

    parameters = {
        "fsym": from_currency,
        "tsym": to_currency,
        "limit": 2000,
        "toTs": end,
        "aggregate": 1
    }

    response = requests.get(f"{api_url}/histoday", params=parameters)

    if response.status_code == 200:
        data = json.loads(response.text)
        transformed_data = []
        

        for d in data["Data"]:
            time_str = datetime.datetime.utcfromtimestamp(d["time"]).strftime("%Y-%m-%d %H:%M")
            transformed_data.append({
                "time": d["time"],
                "value": d["close"]
            })
        pair.chart_data = transformed_data
        pair.save()

        return JsonResponse(transformed_data, safe=False)
    else: 
        print("Error getting historical data")
    
    return None

def update_new_data(request, account):
    user = request.user  # Make sure to retrieve the user
    trading_account = Account.objects.get(user=request.user, account_type=account)
    account_balance = trading_account.balance
    trades = OptionTrade.objects.filter(trader=trading_account, expired=False).order_by('-id')
    closed_trades = OptionTrade.objects.filter(trader=trading_account, expired=True).order_by('-id')
    update_trade_outcomes(request)

    # Convert the queryset to a list of dictionaries
    trades_data = serializers.serialize('python', trades)

    # Serialize the closed trades
    closed_trades_data = serializers.serialize('python', closed_trades)

    print(f"New Balance {account_balance}")

    new_data = {
        'trades': trades_data,
        'closed_trades': closed_trades_data,
        'demo_account_balance': account_balance,
    }
    return JsonResponse(new_data)
    
def get_forex_historical_data(request, symbol):
    from_currency = symbol[:3]
    print(f"Historical Data Symbol {symbol}")
    to_currency = symbol[3:]

    pair = ForexPair.objects.get(symbol=symbol)
    start = int(datetime.datetime(2023, 1, 1).timestamp())
    end = int(datetime.datetime.now().timestamp())
    api_url = "https://min-api.cryptocompare.com/data"
    Exchage = "CCCAGG"

    parameters = {
        "fsym": from_currency,
        "tsym": to_currency,
        "limit": 2000,
        "e": Exchage,
        "toTs": end,
        "aggregate": 1
    }

    response = requests.get(f"{api_url}/histominute", params=parameters)

    if response.status_code == 200:
        data = json.loads(response.text)
        transformed_data = []

        # In transform loop
        for d in data["Data"]:
            time_str = datetime.datetime.utcfromtimestamp(d["time"]).strftime("%Y-%m-%d %H:%M")
            timestamp = int(datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M").timestamp())

            price = d["close"]
            # Format with 4 decimals
            formatted_price = "{:.5f}".format(price)
            
            transformed_data.append({
                "time": timestamp,
                "value": d["close"]
            })

        pair.chart_data = transformed_data
        pair.save()


        return JsonResponse(transformed_data, safe=False)
        
    else: 
        print("Error getting historical data")
    
    return None

def get_crypto_chart_data(request, symbol):
    from_currency = symbol[:3]
    print(f"Historical Data Symbol {symbol}")
    to_currency = symbol[3:]

    pair = CryptoPair.objects.get(symbol=symbol)
    start = int(datetime.datetime(2023, 1, 1).timestamp())
    end = int(datetime.datetime.now().timestamp())
    api_url = "https://min-api.cryptocompare.com/data"
    Exchage = "CCCAGG"

    parameters = {
        "fsym": from_currency,
        "tsym": to_currency,
        "limit": 2000,
        "e": Exchage,
        "toTs": end,
        "aggregate": 1
    }

    response = requests.get(f"{api_url}/histominute", params=parameters)

    if response.status_code == 200:
        data = json.loads(response.text)
        transformed_data = []

        # In transform loop
        for d in data["Data"]:
            time_str = datetime.datetime.utcfromtimestamp(d["time"]).strftime("%Y-%m-%d %H:%M")
            timestamp = int(datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M").timestamp())

            price = d["close"]
            # Format with 4 decimals
            formatted_price = "{:.5f}".format(price)
            
            transformed_data.append({
                "time": timestamp,
                "value": d["close"]
            })

        pair.chart_data = transformed_data
        pair.save()


        return JsonResponse(transformed_data, safe=False)
        
    else: 
        print("Error getting historical data")
    
    return None




def get_tiingo_forex_data(request, symbol):

    TIINGO_API_KEY = "4e5b7c893bd98207a7b4d53d4b1415e152fda4e2"

    # Construct API URL
    url = f"https://api.tiingo.com/tiingo/fx/{symbol}/prices"

    today = datetime.datetime.now()
    year_ago = today - datetime.timedelta(days=365)

    params = {
        "startDate": year_ago.strftime("%Y-%m-%d"),
        "resampleFreq": "5min", # 5 minute intervals
        "token": TIINGO_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        transformed_data = []
        for d in data:
            # Ensure that the date string includes milliseconds
            date_string = d["date"][:-1] + "Z"  # Adding "Z" to indicate UTC timezone
            timestamp = int(datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())

            close = float(d["close"])

            transformed_data.append({
                "time": timestamp,
                "value": close
            })

        pair = ForexPair.objects.get(symbol=symbol)
        pair.chart_data = transformed_data
        pair.save()

        return JsonResponse(transformed_data, safe=False)

    except Exception as e:
        print("Request failed:", e)

    return None

def get_currencybeacon_forex_data(request, symbol):
    API_KEY = "e8ReRqK75K6fAv2qLLfWuAHaXVfx4lcq"

    base = symbol[:3]
    quote = symbol[3:]
    
    url = f"https://api.currencybeacon.com/v1/timeseries"

    today = datetime.datetime.now()
    year_ago = today - datetime.timedelta(days=7)

    time_now = today.strftime("%Y-%m-%d %H:%M")

    print(f"Time Now: {time_now}")

    params = {
        "base": base,
        "symbols": quote,
        "start_date": year_ago.strftime("%Y-%m-%d"),
        "end_date": time_now,
        "api_key": API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()["data"]

        transformed_data = []
        for d in data:
            timestamp = int(datetime.datetime.fromisoformat(d["date"]).timestamp())
            rate = float(d["rate"])
            formatted_rate = "{:.5f}".format(rate)

            transformed_data.append({
                "time": timestamp,
                "value": formatted_rate  
            })

        pair = ForexPair.objects.get(symbol=symbol)  
        pair.chart_data = transformed_data
        pair.save()

        return JsonResponse(transformed_data, safe=False)

    except Exception as e:
        print("Request failed:", e)
    
    return None

def get_polygon_forex_data(request, symbol):
    pair = ForexPair.objects.get(symbol=symbol)

    POLYGON_API_KEY = "kK2tNnUCKcv5hkI75sGJdVJHv0mRXypY" 
    now = int(time.time() * 1000)
    start = now - (7 * 24 * 60 * 60 * 1000)
    today = datetime.datetime.now()
    week_ago = today - datetime.timedelta(days=5)
    from_time = week_ago.strftime("%Y-%m-%d")
    to_time = today.strftime("%Y-%m-%d %H:%M")
    limit = 10000, # max
    # Get the current time in seconds since the Unix epoch


    # Print the current timestamp
    print(f"Time Now {to_time}")
    print(f"Used time {now}")
    print(f"Start Time {start}")

    url = f"https://api.polygon.io/v2/aggs/ticker/C:{symbol}/range/1/minute/{start}/{now}?adjusted=true&sort=desc&limit=5000&apiKey=kK2tNnUCKcv5hkI75sGJdVJHv0mRXypY"


    try:
        response = requests.get(url)
        results = response.json()["results"]

        transformed_data = []
        for r in results:
            dt = datetime.datetime.fromtimestamp(r["t"]/1000)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
            timestamp = int(datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M").timestamp())

            close = (r["c"])

            transformed_data.append({
                "time": timestamp,
                "value": close
            })

        pair.chart_data = transformed_data
        pair.save()

        return JsonResponse(transformed_data, safe=False)

    except Exception as e:
        print("Request failed:", e)
    
    return None

def markers_chart(request):
    return render(request, 'marker_charts.html')

def dashboard(request, account):
    user = request.user
    wallet = Account.objects.get(user=user ,account_type='WALLET')
    trading_account = Account.objects.get(user=request.user, account_type=account)
    margin_trades = Trade.objects.filter(trader=trading_account, assets_type='CRYPTO').order_by('-id')
    options_trades = OptionTrade.objects.filter(trader=trading_account, expired=True, assets_type='CRYPTO').order_by('-id')[:10]

    transactions = Transaction.objects.filter(trader=trading_account)[:10]

    margin_transaction_descriptions = ["Buy Margin Trade", "Sell Margin Trade"]
    margin_transactions = Transaction.objects.filter(trader=trading_account, description__in=margin_transaction_descriptions)[:5]

    options_transaction_descriptions = ["Buy Options Trade", "Sell Options Trade"]
    options_transactions = Transaction.objects.filter(trader=trading_account, description__in=options_transaction_descriptions).order_by('-id')[:5]
    print(f"Margin Transactions: {margin_transactions}")
    print(f"Options Transactions: {options_transactions}")
    # Transform format 
    chart_date = []
    chart_balance = []

    margin_chart_date = []
    margin_chart_balance = []

    options_chart_date = []
    options_chart_balance = []

    for transaction in transactions:
        # Extract month abbreviation, day, hour, and minute
        formatted_date = transaction.date.strftime('%b %d %H.%M')
        chart_date.append(formatted_date)

        # Convert Decimal to integer and append to the chart_balance list
        chart_balance.append(int(transaction.balance))

    for margin_transaction in margin_transactions:
        # Extract month abbreviation, day, hour, and minute
        formatted_date = margin_transaction.date.strftime('%b %d %H.%M')
        margin_chart_date.append(formatted_date)

        # Convert Decimal to integer and append to the chart_balance list
        margin_chart_balance.append(int(margin_transaction.balance))

    for options_transaction in options_transactions:
        # Extract month abbreviation, day, hour, and minute
        formatted_date = options_transaction.date.strftime('%b %d %H.%M')
        options_chart_date.append(formatted_date)

        # Convert Decimal to integer and append to the chart_balance list
        options_chart_balance.append(int(options_transaction.balance))

        
    print(f"Chart Date: {chart_date}")
    print(f"Chart Balance: {chart_balance}")

    context = {
        'user': user,
        'wallet': wallet,
        'chart_date': chart_date,
        'chart_balance': chart_balance,
        'margin_chart_date': margin_chart_date,
        'margin_chart_balance': margin_chart_balance,
        'options_chart_date': options_chart_date,
        'options_chart_balance': options_chart_balance,
        'account': account,
        'margin_trades': margin_trades,
        'options_trades': options_trades,
    }
    
    return render(request, 'dashboard/index.html', context)

def add_funds(request, account):

    context = {
        'account': account,
    }
    return render(request, 'dashboard/icons.html', context)

def withdraw_funds(request, account):
    context = {
        'account': account,
    }
    return render(request, 'dashboard/map.html', context)

def notification(request, account):
    context = {
        'account': account,
    }
    return render(request, 'dashboard/notifications.html', context)

def deposit_eth(request, account):
    context = {
        'account': account,
    }
    return render(request, 'deposit_eth.html', context)

def deposit_usdt(request, account):
    context = {
        'account': account,
    }
    return render(request, 'deposit_usdt.html', context)

def deposit_usdc(request, account):
    context = {
        'account': account,
    }
    return render(request, 'deposit_usdc.html', context)


def contest(request, account):
    context = {
        'account': account,
    }
    return render(request, 'dashboard/tables.html', context)

def all_trades(request, account):

    user = request.user

    trading_account = Account.objects.get(user=request.user, account_type=account)

    trades = OptionTrade.objects.filter(trader=trading_account, expired=False, assets_type='CRYPTO').order_by('-id')

    margin_trades = Trade.objects.filter(trader=trading_account, assets_type='CRYPTO').order_by('-id')
    closed_trades = OptionTrade.objects.filter(trader=trading_account, expired=True, assets_type='CRYPTO').order_by('-id')[:10]

    context = {
        'account': account,
        'trades': trades,
        'margin_trades': margin_trades,
        'closed_trades': closed_trades,
        'user': user,
    }

    return render(request, 'all_trades.html', context)

def trader_profile(request, account):
    user = request.user
    live_account = Account.objects.filter(user=request.user, account_type='LIVE')  # Use 'objects' instead of 'object'.
    demo_account = Account.objects.get(user=request.user, account_type='DEMO')
    demo_account_balance = demo_account.account_id
    print(f"Account ID {demo_account_balance}")
    profile = Profile.objects.get(username=user)  # Use 'objects.get' to retrieve a single object.

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        address = request.POST['address']
        city = request.POST['city']
        country = request.POST['country']
        zip_code = request.POST['zip_code']
        dob = request.POST['dob']
        gender = request.POST['gender']
        mobile_no = request.POST['mobile_no']
        about = request.POST['about']

        profile.first_name = first_name
        profile.last_name = last_name
        profile.address = address
        profile.city = city
        profile.country = country
        profile.zip_code = zip_code
        profile.dob = dob
        profile.gender = gender
        profile.mobile_no = mobile_no
        profile.about = about

        profile.save()

        return redirect('trader_profile')


    context = {
        'user': user,
        'account_id': demo_account_balance,
        'live_account': live_account,
        'demo_account': demo_account,
        'profile': profile,
        'account': account
    }

    return render(request, 'dashboard/user.html', context)  # Ensure you close the 'render' function properly.)

def selected_pair(request, currency_pair, account):
    user = request.user
    pairs = ForexPair.objects.all()
    # Existing code...
    forex_pairs = ForexPair.objects.all()
    forex_prices = {}
    trading_account = Account.objects.get(user=request.user, account_type=account)
    trades = Trade.objects.filter(trader=trading_account)
    # Retrieve all open trades for the user
    open_trades = Trade.objects.filter(trader=trading_account, is_active=True)

    # Calculate the equity for each open trade and sum them up
    total_equity = sum(trade.equity for trade in open_trades)

    for forex_pair in forex_pairs:
        pair_data = ForexPair.objects.get(pair=forex_pair.pair)

        if pair_data.chart_data:
            chart_data = pair_data.chart_data
            latest_point = chart_data[-1]
            price = latest_point['value']
        
        else:
            price = None

        if price:
            forex_prices[forex_pair] = price
            print(f"Pair: {forex_pair}, Price: {price}")

    currency = ForexPair.objects.get(symbol=currency_pair)
    print(f"Currency: {currency.pair}")


    # Get the user's account balance
    trading_account_balance = trading_account.balance
    # Add the total equity to the demo account balance
    balance_equity = trading_account_balance + total_equity

    open_positions = []  # Retrieve user's open positions from the database
    transaction_history = []  # Retrieve user's transaction history from the database
    pair_price = get_forex_price(currency.pair)

    print(f"Currency Pair: {currency_pair}, Price: {pair_price}")
    context = {
        'currency_pair': currency_pair,
        'trades': trades,
        'pair_price': pair_price,
        'forex_prices': forex_prices,
        'price': price,
        'account': account,
        'account_balance': trading_account_balance,
        'open_positions': open_positions,
        'transaction_history': transaction_history,
        'demo_account_balance': trading_account_balance,
        'balance_equity': balance_equity,
        'user': user,
    }
    return render(request, 'trading.html', context)

def crypto_selected_pair(request, currency_pair, account):
    user = request.user
    pairs = CryptoPair.objects.all()
    # Existing code...
    forex_pairs = CryptoPair.objects.all()
    forex_prices = {}
    trading_account = Account.objects.get(user=request.user, account_type=account)
    trades = Trade.objects.filter(trader=trading_account, assets_type='CRYPTO')
    # Retrieve all open trades for the user
    open_trades = Trade.objects.filter(trader=trading_account, is_active=True, assets_type='CRYPTO')

    # Calculate the equity for each open trade and sum them up
    total_equity = sum(trade.equity for trade in open_trades)

    for forex_pair in forex_pairs:
        pair_data = CryptoPair.objects.get(pair=forex_pair.pair)

        if pair_data.candle_chart_data:
            chart_data = pair_data.candle_chart_data
            latest_point = chart_data[-1]
            price = latest_point['close']
        
        else:
            price = None

        if price:
            forex_prices[forex_pair] = price
            print(f"Pair: {forex_pair}, Price: {price}")

    currency = CryptoPair.objects.get(symbol=currency_pair)
    print(f"Currency: {currency.pair}")


    # Get the user's demo account balance
    demo_account = Account.objects.get(user=request.user, account_type='DEMO')
    demo_account_balance = demo_account.balance
    # Add the total equity to the demo account balance
    balance_equity = demo_account_balance + total_equity

    account_balance = 10000.00  # Retrieve user's account balance from the database
    open_positions = []  # Retrieve user's open positions from the database
    transaction_history = []  # Retrieve user's transaction history from the database
    pair_price = get_forex_price(currency.pair)

    print(f"Currency Pair: {currency_pair}, Price: {pair_price}")
    context = {
        'symbol': currency_pair,
        'trades': trades,
        'pair_price': pair_price,
        'forex_prices': forex_prices,
        'price': price,
        'account': account,
        'account_balance': account_balance,
        'open_positions': open_positions,
        'transaction_history': transaction_history,
        'demo_account_balance': demo_account_balance,
        'balance_equity': balance_equity,
        'user': user,
    }
    return render(request, 'dashboard/includes/trading_panel.html', context)


def place_trade(request, direction, account):
    user = request.user
    trading_account = Account.objects.get(user=request.user, account_type=account)
    trading_account_balance = trading_account.balance
    if request.method == 'POST':
        # Get the take profit, stop loss, and lot size from the form submission
        take_profit = request.POST.get('take_profit')
        stop_loss = request.POST.get('stop_loss')
        entry = request.POST.get('entry')
        lot_size = request.POST.get('lot_size')
        symbol = request.POST.get('symbol')

        pair = ForexPair.objects.get(symbol=symbol)

        
        # Save the trade details to the database
        trade = Trade.objects.create(
            trader=trading_account,
            trade_direction=direction,
            entry=entry,
            take_profit=take_profit,
            stop_loss=stop_loss,
            lot_size=lot_size,
            symbol=symbol,
            icon=pair.image
        )
        trade.save()

        
        # Pass the scraped symbol and other trade details to the template
        context = {
            'direction': direction,
            'take_profit': take_profit,
            'account': account,
            'stop_loss': stop_loss,
            'lot_size': lot_size,
            'entry': entry,
            'symbol': symbol,
        }

        return render(request, 'trade_success.html', context)

    # If the request method is not POST, render the form page
    return render(request, 'place_trade_form.html')

def place_crypto_trade(request, direction, account):
    user = request.user
    trading_account = Account.objects.get(user=request.user, account_type=account)
    if request.method == 'POST':
        # Get the take profit, stop loss, and lot size from the form submission
        take_profit = request.POST.get('take_profit')
        stop_loss = request.POST.get('stop_loss')
        entry = request.POST.get('entry')
        lot_size = request.POST.get('lot_size')
        symbol = request.POST.get('symbol')

        pair = CryptoPair.objects.get(symbol=symbol)
        
        # Save the trade details to the database
        trade = Trade.objects.create(
            trader=trading_account,
            assets_type='CRYPTO',
            trade_direction=direction,
            entry=entry,
            take_profit=take_profit,
            stop_loss=stop_loss,
            lot_size=lot_size,
            symbol=symbol,
            icon=pair.image
        )
        trade.save()

        transaction = Transaction.objects.create(
            trader=trading_account,
            description= "Buy Margin Trade",
            transaction_id= trading_account.account_id + str(random.randint(1000000, 9999999)),
            amount = lot_size,
            balance= trading_account.balance
        )
        transaction.save()
        # Pass the scraped symbol and other trade details to the template
        context = {
            'direction': direction,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'account': account,
            'lot_size': lot_size,
            'entry': entry,
            'symbol': symbol,
        }

        return render(request, 'trade_success.html', context)

    # If the request method is not POST, render the form page
    return render(request, 'place_trade_form.html')

# views.py
def place_option_trade(request, option_type, account):
    user = request.user
    trading_account = Account.objects.get(user=request.user, account_type=account)
    trading_account_balance = trading_account.balance
    
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        stake = request.POST.get('stake')
        expiration = int(request.POST.get('expiration')) 
        pair = get_object_or_404(CryptoPair, symbol=symbol)
        chart_data = pair.chart_data

        last_point = chart_data[-1]
        strike_price = last_point['value']
        strike_time = last_point['time']

        exp_time = strike_time + expiration * 60

        trading_account_balance = trading_account.balance - Decimal(stake)
        trading_account.balance = trading_account_balance
        trading_account.save()

        # Convert timestamp to datetime
        dt = datetime.datetime.fromtimestamp(last_point['time'])

        close_ex = datetime.timedelta(minutes=expiration)
        print(f"Close ex {close_ex}")

        open_time = datetime.datetime.now(timezone.utc)

        # Calculate expiration time in minutes
        expire_time = open_time + datetime.timedelta(minutes=expiration)

        print(f"{option_type} {symbol} at {strike_price} during {strike_time} to expire in {expire_time} minutes")

        option = OptionTrade.objects.create(
            trader=trading_account,
            symbol = symbol,
            expiration = expiration,
            assets_type = 'CRYPTO',
            strike_price = strike_price,
            option_type = option_type,
            stake = stake,
            expire_time = exp_time,
            close_time=expire_time,
            open_time=open_time,
        )
        option.save()

        transaction = Transaction.objects.create(
            trader=trading_account,
            description= "Buy Options Trade",
            transaction_id= trading_account.account_id + str(random.randint(1000000, 9999999)),
            amount = f"-{stake}",
            balance= trading_account.balance
        )
        transaction.save()
        strike_price = option.strike_price

        response_data = {
            'strike_price': strike_price,
            'expiration': expiration  # Include expiration here
        }

        print(f"strike price {strike_price}")
        return JsonResponse({'strike_price': strike_price})
    else:
        # Invalid request
        return HttpResponseBadRequest()

def place_candleoption_trade(request, option_type):
    user = request.user
    demo_account = Account.objects.get(user=request.user, account_type='DEMO')
    demo_account_balance = demo_account.balance
    
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        stake = request.POST.get('stake')
        expiration = int(request.POST.get('expiration'))
        pair = get_object_or_404(ForexPair, symbol=symbol)
        chart_data = pair.candle_chart_data

        last_point = chart_data[-1]
        strike_price = last_point['close']
        strike_time = last_point['time']

        demo_account_balance = demo_account.balance - Decimal(stake)
        demo_account.balance = demo_account_balance
        demo_account.save()

        # Convert timestamp to datetime
        dt = datetime.datetime.fromtimestamp(last_point['time'])

        # Calculate expiration time in minutes
        expire_time = strike_time + (expiration * 60)

        print(f"{option_type} {symbol} at {strike_price} during {strike_time} to expire in {expire_time} minutes")

        option = OptionTrade.objects.create(
            trader=user,
            symbol = symbol,
            expiration = expiration,
            strike_price = strike_price,
            option_type = option_type,
            stake = stake,
            close_time=expire_time
        )
    
        strike_price = option.strike_price

        response_data = {
            'strike_price': strike_price,
            'expiration': expiration  # Include expiration here
        }

        print(f"strike price {strike_price}")
        return JsonResponse({'strike_price': strike_price})

    else:
        # Invalid request
        return HttpResponseBadRequest()

def support(request):
    return render (request, 'support.html')

def chartpage(request):
    return render(request, 'options_charts/index.html')

def update_trade_outcomes(request):
    now = timezone.now()
    user = request.user
    demo_account = Account.objects.get(user=request.user, account_type='DEMO')
    demo_account_balance = demo_account.balance
    live_account = Account.objects.get(user=request.user, account_type='LIVE')
    live_account_balance = live_account.balance
    demo_trades = OptionTrade.objects.filter(trader=demo_account, expired=False)
    live_trades = OptionTrade.objects.filter(trader=live_account, expired=False)

    for demo_trade in demo_trades:
        print(f"Checking trade outcome for {demo_trade}.")
        try:
            forex_pair = CryptoPair.objects.get(symbol=demo_trade.symbol)
            closing_time = demo_trade.close_time
            open_time = demo_trade.open_time
            expiry_time = demo_trade.expire_time
            # Get the current time
            time_now = datetime.datetime.now(timezone.utc)
            demo_trade.time_now = time_now.strftime("%M:%S")
            demo_trade.save()

            print(f"Current time {demo_trade.time_now}")

            # Convert it to a timestamp (Unix timestamp)
            # timestamp = current_time.timestamp()

            countdown = closing_time - demo_trade.time_now
            print(f"Coundown time {time_now}")

            # Assume 'countdown' is in seconds
            # minutes = int(countdown // 60)
            # seconds = int(countdown % 60)
            # # Create a timedelta object with minutes and seconds
            # countdown_timedelta = datetime.timedelta(minutes=minutes, seconds=seconds)
            # default=timezone.now() + timezone.timedelta(hours=5)
            demo_trade.countdown = countdown
            demo_trade.save()
            countdown_str = str(countdown)  # Convert the timedelta to a string

            if "day" in countdown_str:
                # Find the corresponding closing price
                last_point = forex_pair.chart_data[-1]

                # Extract the 'value' from the last point as the closing price.
                closing_price = last_point['value']

                demo_trade.closing_price = closing_price
                demo_trade.save()

                outcome = demo_trade.calculate_outcome()
                demo_trade.outcome = outcome
                demo_trade.expired = True
                demo_trade.save()

                trading_account = Account.objects.get(user=request.user, account_type='DEMO')
                
                print(f"trade outcome for {demo_trade.symbol} updated")
                print(f" Outcome is {outcome} ")

                # Update demo account balance based on trade outcome
                if outcome == 'won':
                    stake_multiplier = 2  # Multiplier for the stake
                    stake = Decimal(demo_trade.stake) * stake_multiplier

                    demo_account_balance = demo_account.balance + stake
                    demo_account.balance = demo_account_balance
                    demo_account.save()

                    transaction = Transaction.objects.create(
                        trader=trading_account,
                        description= "Sell Options Trade",
                        transaction_id= trading_account.account_id + str(random.randint(1000000, 9999999)),
                        amount = stake,
                        balance= demo_account_balance
                    )
                    transaction.save()
                    # Mark the trade as expired after updating the balance
                    
                    demo_trade.save()
                    print(f"Demo account balance updated: {demo_account_balance}")
                else:
                    transaction = Transaction.objects.create(
                        trader=trading_account,
                        description= "Sell Options Trade",
                        transaction_id= trading_account.account_id + str(random.randint(1000000, 9999999)),
                        amount = 0.00,
                        balance= demo_account_balance
                    )
                    transaction.save()
            else:
                print(f"Closing time not found")
        except ForexPair.DoesNotExist:
            print(f"ForexPair Doesn't exist")
            pass

    for live_trade in live_trades:
        print(f"Checking trade outcome for {live_trade}.")
        try:
            forex_pair = ForexPair.objects.get(symbol=live_trade.symbol)
            closing_time = live_trade.close_time
            open_time = live_trade.open_time
            expiry_time = live_trade.expire_time
            # Get the current time
            time_now = datetime.datetime.now(timezone.utc)
            live_trade.time_now = time_now.strftime("%M:%S")
            live_trade.save()

            print(f"Current time {live_trade.time_now}")

            # Convert it to a timestamp (Unix timestamp)
            # timestamp = current_time.timestamp()

            countdown = closing_time - live_trade.time_now
            print(f"Coundown time {time_now}")

            # Assume 'countdown' is in seconds
            # minutes = int(countdown // 60)
            # seconds = int(countdown % 60)
            # # Create a timedelta object with minutes and seconds
            # countdown_timedelta = datetime.timedelta(minutes=minutes, seconds=seconds)
            # default=timezone.now() + timezone.timedelta(hours=5)
            live_trade.countdown = countdown
            live_trade.save()
            countdown_str = str(countdown)  # Convert the timedelta to a string

            if "day" in countdown_str:
                # Find the corresponding closing price
                last_point = forex_pair.chart_data[-1]

                # Extract the 'value' from the last point as the closing price.
                closing_price = last_point['value']

                live_trade.closing_price = closing_price
                live_trade.save()

                outcome = live_trade.calculate_outcome()
                live_trade.outcome = outcome
                live_trade.expired = True
                live_trade.save()
                print(f"trade outcome for {live_trade.symbol} updated")
                print(f" Outcome is {outcome} ")

                trading_account = Account.objects.get(user=request.user, account_type='LIVE')
                # Update demo account balance based on trade outcome
                if outcome == 'won':
                    stake_multiplier = 2  # Multiplier for the stake
                    stake = Decimal(live_trade.stake) * stake_multiplier

                    live_account_balance = live_account.balance + stake
                    live_account.balance = live_account_balance
                    live_account.save()

                    transaction = Transaction.objects.create(
                        trader=trading_account,
                        description= "Sell Options Trade",
                        transaction_id= trading_account.account_id + str(random.randint(1000000, 9999999)),
                        amount = stake,
                        balance= live_account_balance
                    )
                    transaction.save()
                    # Mark the trade as expired after updating the balance
                    
                    live_trade.save()
                    print(f"Demo account balance updated: {demo_account_balance}")
                else:
                    transaction = Transaction.objects.create(
                        trader=trading_account,
                        description= "Sell Options Trade",
                        transaction_id= trading_account.account_id + str(random.randint(1000000, 9999999)),
                        amount = 0.00,
                        balance= live_account_balance
                    )
                    transaction.save()
            else:
                print(f"Closing time not found")
        except ForexPair.DoesNotExist:
            print(f"ForexPair Doesn't exist")
            pass

    return HttpResponse("Trade outcomes updated.")

class OptionsView(View):
    def post(self, request):
        user = request.user

        trade_type = request.data['trade_type']
        symbol = request.data['symbol']
        strike_price = request.data['strike_price']
        expiry_date = request.data['expiry_date']

        trade = Trade.objects.create(
            user=user,
            trade_type=trade_type,
            symbol=symbol,
            strike_price=strike_price,
            expiry_date=expiry_date
        )

        # Emit trade via websocket

        return JsonResponse({'status': 'created'})

def chart_view(request):
    symbol = 'LIONTC'  # Default symbol

    try:
        forex_pair = ForexPair.objects.get(symbol=symbol)
        chart_data = json.loads(forex_pair.chart_data)
    except ForexPair.DoesNotExist:
        chart_data = []

    context = {
        'chart_data': json.dumps(chart_data)
    }

    return render(request, 'charts.html', context)


def get_crypto_price(request):
    CRYPTOCOMPARE_API_URL = "https://min-api.cryptocompare.com/data"

    parameters = {
        "fsym": "EUR",
        "tsyms": "USD"
    } 

    response = requests.get(f"{CRYPTOCOMPARE_API_URL}/price", params=parameters)

    if response.status_code == 200:
        data = response.json()
        price = data["USD"]
        print(f"ETH/USD price: {price}")
        return JsonResponse({"price": price})
    else:
        print("Error getting BTC price")  
        return JsonResponse({"error": "Error getting BTC price"}, status=500)

def generate_candle_data(request):

    num_points = 30000
    
    now = datetime.now().replace(second=0, microsecond=0)
    start = datetime.now() - timedelta(hours=num_points-4)
    start_timestamp = int(datetime.timestamp(start))

    data = []

    for i in range(num_points):

        open = uniform(50, 60)
        high = open + uniform(0, 5)
        low = open - uniform(0, 5)
        close = uniform(low, high)

        point = {
        "time": start.strftime("%Y-%m-%d %H:%M"),
        "open": open,
        "high": high,
        "low": low,
        "close": close
        }

        data.append(point)
        start += timedelta(minutes=1)

    data[-1]["time"] = now.isoformat()
    
    return data

def update_chart_data(request, symbol):
    print(f"Updating chart data {symbol}")

    try:
        pair = ForexPair.objects.get(symbol=symbol)

    except ForexPair.DoesNotExist:
        return JsonResponse({'error': 'Invalid symbol'})
    
    if symbol == 'LIONTC':
        # Get existing data 
        data = pair.chart_data 

        # Generate new point
        last_point = data[-1]
        
        # Check the length of the timestamp and parse accordingly
        last_time = last_point['time']
        
        if len(last_time) == 10:
            last_time += ':00'
        
        next_time = datetime.datetime.strptime(last_time, '%Y-%m-%d') + datetime.timedelta(minutes=1)
        next_value = last_point['value'] + (random.random() - 0.5) * 5

        new_point = {
            'time': next_time.strftime('%Y-%m-%d'),
            'value': next_value
        }

        # Append new point
        data.append(new_point)

        # Save updated data
        pair.chart_data = data
        pair.save()

        return JsonResponse(new_point)

    else:
        print(f"Searching price for {symbol}")
        # Get price from Alpha Vantage
        data = pair.chart_data 
        exchange_rate = get_alpha_vantage_price(pair.pair)
        
        if exchange_rate:
            print(f"Exchage rate found for {symbol}")

            # Generate new data point
            new_point = {
                'time': datetime.now().strftime('%Y-%m-%d'), 
                'value': exchange_rate
            }

            # Append to chart data
            pair.chart_data.append(new_point)

            # Save updated data
            pair.chart_data = data
            pair.save()
            print(f"New chart data for {symbol} saved")

            return JsonResponse(new_point)
        else:
            print(f"Exchage rate {symbol} not found")

class ChartDataView(View):
    def get(self, request):
        symbol = request.GET.get('symbol')

        # Get chart data

        data = {
        'labels': [],
        'datasets': [
            {
            'label': symbol,
            'data': [] 
            }
        ]
        }

        return JsonResponse(data)

