from .models import *
from payid.models import *
from blockchain.v2 import receive
import requests
import os
from django.http import HttpResponse
from django.conf import settings
# from blockchain.wallet import Wallet
# from blockchain import util 

import json
import time
import decimal
from . import bitgo_utils
# from .try_sign import get_mnemonic_code
# from xrpl_wallet.funding_transactions import set_trust_lines
def create_xrpl_wallet_and_bitcoin_addresss(user):
    logger.info("came in create_xrpl_wallet_and_bitcoin_addresss ")
    try:
        user_profile_obj = UserProfile.objects.get(user=user)
        payid_obj = PayId.objects.create(user_profile=user_profile_obj,name=user.username)
        logger.info('payid is created')
    except Exception as e:
        logger.info('Error in create Payid=',str(e))

    create_xrpl_address(user_profile_obj)
    create_bitcoin_address(user_profile_obj)
    return 

def create_xrpl_address(user_profile_obj):
    logger.info("came in create_xrpl_wallet ")

    xrpl_server_ip = settings.xrpl_SERVER
    payid_obj= PayId.objects.get(user_profile=user_profile_obj)
    if settings.PRODUCTION_ENV:
        xrpl_server_url = "http://"+str(xrpl_server_ip)
        to_send = {
                "method": "wallet_propose",
                "params": [{}]
            }

        logger.info("riplle server url is ",xrpl_server_url)
        try:
            response = requests.post(xrpl_server_url, json=to_send)
            response.raise_for_status()
        except  Exception as e:
            logger.info("error in wallet propose is",e)
            return
        json_response = response.json()
        # logger.info("response in wallet propose is ",json_response)
        result = json_response['result']

        xrpl_wallet_obj  = xrplWallet(user=user_profile_obj.user)
        xrpl_wallet_obj.account_id = result['account_id']
        xrpl_wallet_obj.key_type = result['key_type']
        xrpl_wallet_obj.public_key = result['public_key']
        xrpl_wallet_obj.public_key_hex = result['public_key_hex']
        xrpl_wallet_obj.save()
        environment = "mainnet"
        address = result['account_id']
    else:
        try:
            response = requests.post("https://faucet.altnet.xrpltest.net/accounts")
            response.raise_for_status()
        except  Exception as e:
            logger.info("error in creating wallet for testnet is",e)
            return
        json_response = response.json()
        logger.info("json_response in testnet is",json_response)
        address = json_response['account']['classicAddress']
        secret_key = json_response['account']['secret']
        balance = json_response['balance']

        xrpl_wallet_obj  = xrplWallet(user=user_profile_obj.user)
        xrpl_wallet_obj.account_id = address
        xrpl_wallet_obj.master_seed = secret_key
        xrpl_wallet_obj.xrpl_balance = decimal.Decimal(balance)
        xrpl_wallet_obj.save()
        environment = "testnet"
    cryptoaddress_xrpl_obj = CryptoAddress.objects.create(paymentNetwork="XRPL",environment=environment,entity=payid_obj,address=address)



def create_bitcoin_address(user_profile_obj):
    logger.info("Creating BitGO address for user ",str(user_profile_obj.user.username))
    payid_obj= PayId.objects.get(user_profile=user_profile_obj)
    label =user_profile_obj.user.username
    generated_address_info = bitgo_utils.generate_address(label)
    if generated_address_info is None:
        logger.info("Some error in generating BITGO Address")
        return
    received_address=generated_address_info['address']
    receiveIndex=generated_address_info['index']
    receiveId = generated_address_info['id']
    receiveChain = generated_address_info['chain']

    bitcoin_wallet_account_object = BitcoinWalletAccount.objects.create(user=user_profile_obj.user,xpub=receiveId,xpriv=str(receiveChain),index=receiveIndex)    

    r_address_obj = FundingAddress.objects.create(
        bitcoin_account=bitcoin_wallet_account_object,
        address=received_address,
        receiveIndex=receiveIndex
    )
    cryptoaddress_btc_obj = CryptoAddress.objects.create(paymentNetwork="BTC",environment='mainnet',entity=payid_obj,address=received_address)
 