from django.shortcuts import render

from django.http import HttpResponseNotFound, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from project1.api.models import UserModel, PurchaseModel, StockModel, new_api_token

from alpha_vantage.timeseries import TimeSeries
import datetime

# don't put this here in real code! you are welcome to use this key if you would like
av_api_key = "B6Z376P6CGR0XAL5"
ts = TimeSeries(key=av_api_key)

"""
You will create many 4 key views here: register, buy, sell, and list

register - allows a user to register and obtain an API token
buy - allows a user to buy some stocks by submitting a symbol and an amount
sell - allows a user to sell some stocks by submitting a symbol and an amount
list - allows a user to see their current portfolio, does not take arguments
"""
from hashlib import md5

@require_http_methods(["POST"])
@csrf_exempt
def register(request):
    fields = ["first_name", "last_name", "username", "password"]

    # check they provided all the right data
    for field in fields:
        if not request.POST.get(field):
            return JsonResponse({'error': f'field - {field} - not found'})

    users = UserModel.objects.filter(username=request.POST.get("username"))
    if len(users) > 0:
        return JsonResponse({'Username taken!'})

    hashed_pw = md5(request.POST.get("password")).hexdigest()
    user = UserModel(
        username=request.POST.get("username"),
        first_name=request.POST.get("first_name"),
        last_name=request.POST.get("last_name"),
        api_token=new_api_token(),
        password=hashed_pw
    )
    user.save()


@require_http_methods(["POST"])
@csrf_exempt
def buy(request):
    fields = ['api_token', 'symbol', 'quantity']

    # check they provided all the right data
    for field in fields:
        if not request.POST.get(field):
            return JsonResponse({'error': f'field - {field} - not found'})

    users = UserModel.objects.filter(api_token=request.POST.get('api_token'))

    # validate user
    if len(users) == 1:
        user = users[0]
    else:
        return JsonResponse({'error': 'No user found with that API token'})

    try:
        symbol, _ = ts.get_quote_endpoint(symbol=request.POST.get('symbol').upper())
    except ValueError:
        return JsonResponse({'error': f'symbol - {request.POST.get("symbol")} - not found'})

    # strip off AlphaVantage's annoying stuff:
    old_keys = [k for k in symbol]
    for k in old_keys:
        new_k = k.split('. ')[1]
        symbol[new_k] = symbol[k]

    cash = user.portfolio.cash

    if cash - int(request.POST.get('quantity')) * float(symbol['price']) < 0:
        return JsonResponse({'error': 'insufficient funds'})

    # update the amount of cash the user has
    user.portfolio.cash -= int(request.POST.get('quantity')) * float(symbol['price'])
    user.portfolio.save(update_fields=['cash'])

    # add a new purchase
    purchase = PurchaseModel(
        user=user,
        symbol=request.POST.get('symbol').upper(),
        price=symbol['price'],
        quantity=int(request.POST.get('quantity'))
    )
    purchase.save()

    stocks = StockModel.objects.filter(portfolio=user.portfolio, symbol=request.POST.get('symbol').upper())

    if stocks:
        stock = stocks[0]
        stock.quantity += int(request.POST.get('quantity'))
        stock.save(update_fields=['quantity'])
    else:
        stock = StockModel(
            portfolio=user.portfolio,
            symbol=request.POST.get('symbol').upper(),
            quantity=int(request.POST.get('quantity'))
        )
        stock.save()

    return JsonResponse({
        'symbol': request.POST.get('symbol').upper(),
        'quantity': int(request.POST.get('quantity')),
        'timestamp': purchase.timestamp,
        'cash_remaining': user.portfolio.cash
    })
    

@require_http_methods(["POST"])
@csrf_exempt
def sell(request):
    fields = ['api_token', 'symbol', 'quantity']

    # check they provided all the right data
    for field in fields:
        if not request.POST.get(field):
            return JsonResponse({'error': f'field - {field} - not found'})

    users = UserModel.objects.filter(api_token=request.POST.get('api_token'))

    # validate user
    if len(users) == 1:
        user = users[0]
    else:
        return JsonResponse({'error': 'No user found with that API token'})

    try:
        symbol, _ = ts.get_quote_endpoint(symbol=request.POST.get('symbol').upper())
    except ValueError:
        return JsonResponse({'error': f'symbol - {request.POST.get("symbol")} - not found'})

    # strip off AlphaVantage's annoying stuff:
    old_keys = [k for k in symbol]
    for k in old_keys:
        new_k = k.split('. ')[1]
        symbol[new_k] = symbol[k]

    stocks = StockModel.objects.filter(symbol=request.POST.get('symbol').upper(), portfolio=user.portfolio)

    # validate user
    if len(stocks) == 1:
        stock = stocks[0]
    else:
        return JsonResponse({'error': 'insufficient quantity of stocks'})

    if int(request.POST.get('quantity')) > stock.quantity:
        return JsonResponse({'error': 'insufficient quantity of stocks'})

    # update the amount of cash the user has
    user.portfolio.cash -= int(request.POST.get('quantity')) * float(symbol['price'])
    user.portfolio.save(update_fields=['cash'])
    stock.quantity += int(request.POST.get('quantity'))
    stock.save(update_fields=['quantity'])
    # add a new purchase
    purchase = PurchaseModel(
        user=user,
        symbol=request.POST.get('symbol').upper(),
        price=symbol['price'],
        quantity=-int(request.POST.get('quantity'))
    )
    purchase.save()
    return JsonResponse({
        'symbol': request.POST.get('symbol').upper(),
        'quantity': int(request.POST.get('quantity')),
        'timestamp': purchase.timestamp,
        'cash_remaining': user.portfolio.cash
    })

@require_http_methods(["GET"])
def list(request):
    fields = ['api_token']

    # check they provided all the right data
    for field in fields:
        if not request.POST.get(field):
            return JsonResponse({'error': f'field - {field} - not found'})

    users = UserModel.objects.filter(api_token=request.POST.get('api_token'))
    # validate user
    if len(users) == 1:
        user = users[0]
    else:
        return JsonResponse({'error': 'No user found with that API token'})

    stocks = StockModel.objects.filter(portfolio=user.portfolio)
    stock_json = []
    for s in stocks:
        symbol, _ = ts.get_quote_endpoint(s.symbol.upper())
        # strip off AlphaVantage's annoying stuff:
        old_keys = [k for k in symbol]
        for k in old_keys:
            new_k = k.split('. ')[1]
            symbol[new_k] = symbol[k]

        jr = {'symbol': s.symbol,
              'quantity': s.quantity,
              'timestamp': symbol['price'],
              'cash_remaining': user.portfolio.cash}
        stock_json.append(jr)
    return JsonResponse({
            'stock_list': stock_json,
            'cash': user.portfolio.cash,
            'timestamp': datetime.datetime.now()
            })
