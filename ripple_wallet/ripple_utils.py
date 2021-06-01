from ripple_wallet.models import *
import decimal
import json
import requests
from .sign import sign_transaction
from.serialize import serialize_object

from blockchain import createwallet


from blockchain.wallet import Wallet

from blockchain import util 
import time
from django.conf import settings






def get_xrp_balance_for_ripple_wallet(account_id):
 #this uses account_info method to calculate xrp balance   
    to_send = {
    "method": "account_info",
    "params": [
        {
            "account": account_id,
            "strict": True,
            "ledger_index": "current",
            "queue": True
        }
            ]
                }
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)
    json_response = response.json()

    logger.info("json_response is ",json_response)

    ripple_balance = json_response['result']['account_data']['Balance']
    logger.info("type of balance @70 is",type(ripple_balance))
    ripple_balance = int(ripple_balance)
    balance_in_xrp = ripple_balance/1000000
    balance_in_xrp = decimal.Decimal(balance_in_xrp)
    logger.info("balance_in_xrp in@74",balance_in_xrp)
    return balance_in_xrp


def get_btc_from_xrp(xrp_amt):
    response = requests.get('https://www.bitstamp.net/api/v2/ticker_hour/xrpbtc/')
    json_response = response.json()
    ask = json_response['ask']
    ask = decimal.Decimal(str(ask))
    return (ask)*xrp_amt

def get_btc_balance_for_ripple_wallet(account_id):
    #this uses account_lines method to calculate btc balance  
    to_send = {
        "method": "account_lines",
        "params": [
            {
                "account": account_id
            }
        ]
    }
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)
    json_response = response.json()

    bitcoin_balance = 0
    lines = json_response['result']['lines']
    length_of_lines = len(lines)
    logger.info("length of lines is",length_of_lines)
    if settings.TEST_ENV:
        for i in range(length_of_lines):
            if lines[i]['currency'] == "BTC":
                bitcoin_balance += decimal.Decimal(lines[i]['balance'])
    else:
        for i in range(length_of_lines):
            if lines[i]['currency'] == "BTC":
                stb_issuer_wallet = CentralWallet.objects.filter(active=True).first().wallet
                issuer_address = stb_issuer_wallet.account_id
                logger.info("issuer address is",issuer_address)
                logger.info("if lines[i]['account'] is",lines[i]['account'])
                # if (lines[i]['account'] == "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B") or lines[i]['account']==issuer_address:
                if account_id==issuer_address:
                    bitcoin_balance += decimal.Decimal(lines[i]['balance'])
                else:
                    if lines[i]['account']==issuer_address:            
                        bitcoin_balance += decimal.Decimal(lines[i]['balance'])

    logger.info("type of bitcoin balance@96 is",type(bitcoin_balance))
    bitcoin_balance = decimal.Decimal(bitcoin_balance)
    logger.info("bitcoin balance @98 is ",bitcoin_balance)

    return bitcoin_balance



def update_all_ripple_accounts():
    #update both xrp and btc balance in ripplewallet(funded) for all users
    logger.info("update_all_ripple_accounts starts")

    ripple_wallet_list = RippleWallet.objects.filter(is_funded=True)
    logger.info("no of funded ripple wallet is",ripple_wallet_list.count())
    for ripple_wallet in ripple_wallet_list:
        account_id = ripple_wallet.account_id
        logger.info("account_id in update_all_ripple_accounts is",account_id)
        balance_in_xrp = get_xrp_balance_for_ripple_wallet(account_id)
        bitcoin_balance = get_btc_balance_for_ripple_wallet(account_id)

        ripple_wallet.ripple_balance = balance_in_xrp
        ripple_wallet.bitcoin_balance = bitcoin_balance
        ripple_wallet.save()
    logger.info("update_all_ripple_accounts ending")
    return



def update_ripple_account(ripple_address):
    logger.info("riplle adress in update riiple account is",ripple_address)
    ripple_wallet = RippleWallet.objects.get(account_id = ripple_address)
    balance_in_xrp = get_xrp_balance_for_ripple_wallet(ripple_address)
    bitcoin_balance = get_btc_balance_for_ripple_wallet(ripple_address)

    ripple_wallet.ripple_balance = balance_in_xrp
    ripple_wallet.bitcoin_balance = bitcoin_balance
    ripple_wallet.save()
    return


def complete_ledgers():
    #this function returns string of 
    logger.info("@594")
    to_send = {
    "method": "server_state",
    "params": [
        {}
    ]
        }
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)

    json_response = response.json()


    complete_ledgers = json_response['result']['state']['complete_ledgers']
    logger.info("sequnec numver is",complete_ledgers)
    return (complete_ledgers)

def ledger_history(lastledgersequence):
    logger.info("@579")
    get_complete_ledgers = complete_ledgers()
    ledger_lists = get_complete_ledgers.split(',')
    for ledger_list in ledger_lists:
        if '-' not in ledger_list:
            continue
        else:
            x = ledger_list.split('-')
            if x[0] <= str(lastledgersequence -3) and x[1]>=str(lastledgersequence):
                return True
            else:
                continue
    return False


def get_lastledgersequence():
    # user = request.user
    to_send = {
    "method": "server_state",
    "params": [
        {}
    ]
        }
 
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)
    json_response = response.json()


    sequence_number = json_response['result']['state']['validated_ledger']['seq']
    logger.info("sequnec numver is",sequence_number)
    return (sequence_number)


def get_sequence_number(account):
    # user = request.user
    to_send = {
        "method": "account_info",
        "params": [
            {
                "account": account,
                "strict": True,
                "ledger_index": "current",
                "queue": True
            }
        ]
    }

    logger.info("ripple submit server is",settings.RIPPLE_SUBMIT_SERVER)
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)
    json_response = response.json()


    sequence_number = json_response['result']['account_data']['Sequence']
    logger.info("get_sequence_number",sequence_number)
    return sequence_number



