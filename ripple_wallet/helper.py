import requests
import decimal
from payid.models import PayId

def get_btc_to_currency(currency_code):
    request_url = env('coinbase_url')+str(currency_code)
    response = requests.get(request_url)
    json_response = response.json()
    btc_to_currency = json_response['data']['amount']
    btc_to_currency = decimal.Decimal(btc_to_currency)
    return btc_to_currency



