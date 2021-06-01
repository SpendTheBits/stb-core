from ripple_wallet.models import  *
import logging
logger = logging.getLogger(__name__)
# from ripple_wallet.models import  TransactionOtpAttempt
from ripple_wallet.submit_tx import sign_and_submit_transaction,single_sign_and_submit_transaction

from ripple_wallet.ripple_utils import (get_lastledgersequence,get_sequence_number,get_btc_from_xrp,
    update_all_ripple_accounts,update_ripple_account)

import requests
import decimal
from django.utils import timezone
import datetime
from datetime import timedelta
from django.conf import settings
from push_notifications.models import APNSDevice, GCMDevice
import string
import random
from withdraw.models import Ledger
from accounts.utils import send_notification




def calculate_bitcoin_amount_to_sent(btc_amount_in_float,funding_transaction_obj):
    logger.info("btc_amount_in_float is ",btc_amount_in_float)
    decimal_value_in_btc = decimal.Decimal(btc_amount_in_float)
    commission_value_in_btc = STBTransaction.get_fundwallet_commission(decimal_value_in_btc)
    
    commisson_to_save = decimal.Decimal(commission_value_in_btc)
    logger.info("commission_value_in_btc is",commisson_to_save)
    funding_transaction_obj.commission = commisson_to_save 


    bitcoin_amount = decimal_value_in_btc - commission_value_in_btc      
    bitcoin_amount = "{:.8f}".format(bitcoin_amount)
    bitcoin_amount = decimal.Decimal(bitcoin_amount)     

    funding_transaction_obj.received = bitcoin_amount 
    funding_transaction_obj.save()

    return bitcoin_amount



def create_fund_transaction_object(tx_hash,user,value_in_btc,confirmations):
    logger.info("create_fund_transaction_object")
    rt_object = FundingTransaction.objects.create(tx_hash=tx_hash,user=user,confirmations=confirmations)
    rt_object.value = value_in_btc
    value_in_cad = Currency.get_equivalent_amount_in_cad(value_in_btc,"BTC")
    logger.info("value_in_cad @54",value_in_cad)
    rt_object.value_in_cad = value_in_cad
    rt_object.save()
    
    app_config_obj = AppConfiguration.objects.filter(active=True).first()

    current_reference_number = app_config_obj.current_fund_transaction_reference_number

    if current_reference_number is None:
        new_refernce_no = "FT1000001"
    else:
        new_refernce_no = current_reference_number[:2]+str(int(current_reference_number[2:])+1)

    rt_object.reference_number = new_refernce_no
    # rt_object.initiate_notification_sent= True


    app_config_obj.current_fund_transaction_reference_number = new_refernce_no
    app_config_obj.save()

    #SEND NOTIFICATION TO USER
    # if not rt
    send_notification(user,"You have an new incoming transfer of "+str(value_in_btc)+" BTC")
    rt_object.save()
    return rt_object



def id_generator(size=8, chars=string.ascii_uppercase+string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def fund_account(customer_address,transaction_type,transaction_id):


    logger.info("customer address is",customer_address)
    account_id = customer_address
    wallet_obj = RippleWallet.objects.get(account_id=account_id)
    
    issuing_wallet = CentralWallet.objects.filter(active=True).first().wallet
    # secret = issuing_wallet.master_seed
    if settings.TEST_ENV:
        secret = issuing_wallet.master_seed
    else:
        secret = issuing_wallet.master_key

    logger.info("issuing_wallet is ",issuing_wallet)
    
    issuing_address = issuing_wallet.account_id
    lastledgersequence = get_lastledgersequence()
    lastledgersequence += 4
    logger.info("lastledgersequence is ",lastledgersequence)
    sequence_number = get_sequence_number(issuing_address)
    tx_json = {
            "Account": issuing_address,
            "Amount": "20000000",
            "Destination": account_id,
            "LastLedgerSequence":lastledgersequence,
            "TransactionType": "Payment",
            "Fee":5000,
            "Sequence":sequence_number,

        }

    xrp_tran_obj = XrpTransaction.objects.create(value_in_xrp=20,sender=issuing_wallet,
        receiver=wallet_obj,transaction_type=transaction_type,related_transaction_id=transaction_id,
        last_ledger_sequence=lastledgersequence,sequence=sequence_number)


    response_dict = sign_and_submit_transaction(tx_json,secret)
    tx_hash = response_dict['tx_hash']
    validated = response_dict['validated']
    error = response_dict['error']
    engine_result = response_dict['engine_result']
    engine_result_message = response_dict['engine_result_message']


    if response_dict['error'] is False:
        logger.info("setting is funded as True",)
        wallet_obj.is_funded = True
        wallet_obj.save()

    xrp_tran_obj.tx_hash = tx_hash
    xrp_tran_obj.is_validated = validated

    xrp_tran_obj.error_code = engine_result
    xrp_tran_obj.error_message = engine_result_message

    xrp_tran_obj.save()

    notes = 'Activation Transaction'

    if transaction_type == 'activation_through_wallet':
        trans_obj = STBTransaction.objects.get(id=transaction_id)
        
    else:
        trans_obj = FundingTransaction.objects.get(id=transaction_id)
        
    reference_number = trans_obj.reference_number
    send_entry_particulars = 'Issued  20 xrp to {} for activation'.format(wallet_obj.user)
    receive_entry_particulars = 'Issued from central wallet for activation'


    currency = 'XRP'
    send_entry_ledger = Ledger.objects.create(user=issuing_wallet.user,particulars=send_entry_particulars,
        currency=currency,amount=-20,notes=notes,reference_number=reference_number)

    receive_entry_ledger = Ledger.objects.create(user=wallet_obj.user,particulars=receive_entry_particulars,
        currency=currency,amount=20,notes=notes,reference_number=reference_number)


    return response_dict


def set_trust_lines(customer_address,secret,is_testing=None): #ADITYAAA
    logger.info("customer address is",customer_address)
    logger.info("@101")
    account_id = customer_address
    wallet_obj = RippleWallet.objects.get(account_id=account_id)
    logger.info("account_id",account_id)

    #this is done because in testnet,acoount is used by many so sequence number nit in our control
    if settings.PRODUCTION_ENV:

        # sequence_number = wallet_obj.current_sequence_number
        # if sequence_number is None:
        sequence_number = get_sequence_number(account_id)

        # wallet_obj.current_sequence_number = sequence_number + 1
        # wallet_obj.save()
    else:
        sequence_number = get_sequence_number(account_id)

    lastledgersequence = get_lastledgersequence()
    lastledgersequence += 4
    logger.info("lastledgersequence is ",lastledgersequence)
    logger.info("sequence_number in @273 is",sequence_number)

    stb_issuer_wallet = CentralWallet.objects.filter(active=True).first().wallet
    issuer = stb_issuer_wallet.account_id

    if settings.TEST_ENV:
        currency_code = "BTC"

        limit = "100000"

    else:
        # currency_code = "BTC"
        # stb_issuer_wallet = CentralWallet.objects.filter(active=True).first().wallet
        # issuer = stb_issuer_wallet.account_id
        
        operational_address = CentralWallet.objects.filter(active=True).first().wallet.account_id
        commission_wallet_list = CommissionWallet.objects.filter(active=True)
        if commission_wallet_list is not None:
            commission_wallet_address = commission_wallet_list.first().wallet.account_id
        else:
            commission_wallet_address = None

        if customer_address == operational_address or customer_address == commission_wallet_address:
            limit = "100000"
        else:
            limit = "100"
        currency_code = "BTC"
        # issuer = "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B"

    tx_json = {
                "Account": account_id,

                "TransactionType": "TrustSet",
                "Fee":"1000",
                "Sequence":sequence_number,
                "LastLedgerSequence":lastledgersequence,
                "LimitAmount": {
                        "currency": currency_code,
                        "issuer": issuer,
                        "value": limit
                        }
            }
    if is_testing is not None:
        response_dict = single_sign_and_submit_transaction(tx_json,secret)
    else:
        response_dict = sign_and_submit_transaction(tx_json,secret)

    return response_dict


def transfer_stb_to_wallet(customer_address,bitcoin_amount,secret_key):
    # user = request.user
    logger.info("@1333")
    wallet_obj = RippleWallet.objects.get(account_id=customer_address)
    if secret_key!="not":
        set_trust_lines(customer_address,secret_key)
    logger.info("bitcoin amount is",bitcoin_amount)
    # value must be str so bitcoin amount has to be made into str
    bitcoin_amount = str(bitcoin_amount)
    logger.info("bitcoin_amount in str is @304",bitcoin_amount)


    issuing_wallet = CentralWallet.objects.filter(active=True).first().wallet


    if settings.TEST_ENV:
        secret = issuing_wallet.master_seed
    else:
        secret = issuing_wallet.master_key
    issuing_address = issuing_wallet.account_id

    sequence_number = get_sequence_number(issuing_address)
    lastledgersequence = get_lastledgersequence()
    lastledgersequence += 4
    logger.info("seqnuce number is ",sequence_number)
    stb_issuer_wallet = CentralWallet.objects.filter(active=True).first().wallet
    issuer = stb_issuer_wallet.account_id
    logger.info("issuing address is",issuing_address)
    tx_json = {
            "Account": issuing_address,

            "Amount" : {
                "currency" : "BTC",
                "value" : bitcoin_amount,
                "issuer" : issuer
            },
            "Destination": customer_address,
            "TransactionType": "Payment",
            "Fee":50,
            "Sequence":sequence_number,
            "LastLedgerSequence":lastledgersequence,
            "Flags":131072

        }

    response_dict = sign_and_submit_transaction(tx_json,secret)
    logger.info("response dict after submit is",response_dict)

    #updating all ripple accounts ripple as well as bitcoin balance
    x = update_ripple_account(customer_address)
    y = update_ripple_account(issuer)
    # try:
    #     result = update_all_ripple_accounts()
    # except Exception as e:
    #     logger.info("error in updating ripple accounts is",e)
    return response_dict


def request_to_set_trust_lines(account_id): #ADITYAAAAAA
    logger.info("request_to_set_trust_lines")
    logger.info("account_id is",account_id)
    wallet_obj = RippleWallet.objects.get(account_id=account_id)
    user = wallet_obj.user
    token_error =True
    while token_error==True:
        token = id_generator()
        try:
            User.objects.get(token = token)
            #if it came here it means token already exists therefore create a new token
            logger.info("tokrn already exists")
        except Exception as e:
            user.token = token
            user.save()
            token_error = False

    logger.info("user is ",user)
    logger.info("token is ",token)
    if GCMDevice.objects.filter(user=user).exists():

        android_devices = GCMDevice.objects.filter(user=user)
        logger.info("android_devices is ",android_devices)
        for device in android_devices:
            try:
                device.send_message("Click on this notification to receive funds",extra={'token':token})
            except Exception as e:
                logger.info("error is",e)
                logger.info("reg id is",device.registration_id)
                continue
            logger.info("message send GCMDevice @251")

    # if APNSDevice.objects.filter(user=user).exists():
    #     android_devices = APNSDevice.objects.filter(user=user)
    #     for device in android_devices:

    #         device.send_message("Click on this notification to receive funds",extra={'token':token})
    #         logger.info("message send GCMDevice @251")


    logger.info("request_to_set_trust_lines is done")
    return


def set_ripple_wallet_to_receive_funds(customer_address,transaction_type,transaction_id):

    sequence_error1 = True
    while (sequence_error1==True):
        response_dict = fund_account(customer_address,transaction_type,transaction_id)
        if response_dict['engine_result']!='tefPAST_SEQ':
            sequence_error1 = False

    x = update_ripple_account(customer_address)

    if response_dict['error'] is True:
        return response_dict

    logger.info("after setting fund in set_ripple_wallet_to_receive_funds came here ")
    response = request_to_set_trust_lines(customer_address)



    # response_dict = set_trust_lines(customer_address)
    logger.info("response_dict after fund account is",response_dict)

    return response_dict


def get_wallet_activation_fee_in_btc():
    return  get_btc_from_xrp(20)


def get_btc_to_currency(currency_code):
    request_url = env('coinbase_cur')+str(currency_code)
    response = requests.get(request_url)
    json_response = response.json()
    btc_to_currency = json_response['data']['amount']
    btc_to_currency = decimal.Decimal(btc_to_currency)
    return btc_to_currency

def get_wallet_activation_fee_in_currency(currency_code):

    wallet_activation_charge_in_btc =  get_wallet_activation_fee_in_btc()

    # btc_to_currency = get_btc_to_currency(currency_code)

    # send_value = wallet_activation_charge_in_btc * btc_to_currency
    send_value = Currency.get_equivalent_amount_in_cad(wallet_activation_charge_in_btc,"BTC")
    send_value = format(send_value, '.2f')
    logger.info("send value is",send_value)
    return send_value



def time_left_before_allowing_transaction(user):
    latest_transaction_object = TransactionOtpAttempt.objects.filter(user=user).first()
    if latest_transaction_object is None:
        return 0
    if latest_transaction_object.is_successful_attempt is True:
        return 0
    if latest_transaction_object.no_of_unsuccessful_attempts is  None:
        return 0
    if latest_transaction_object.no_of_unsuccessful_attempts < 5:
        return 0

    modified_date = latest_transaction_object.modified_date
    timedelta = timezone.now() - modified_date
    timedelta = int(timedelta.seconds/60)
    timedelta = timedelta + 1
    logger.info("timedelta is ",timedelta)
    minutes_passed = timedelta
    logger.info("minutes passed is",minutes_passed)
    if minutes_passed > 30:
        return 0
    time_left = 30 - minutes_passed

    logger.info("time left is",time_left)
    return time_left





def check_if_less_than_cad(amount,currency_code,cad):

    btc_in_cad = cad / (get_btc_to_currency("CAD")) 
    if currency_code=="BTC":
        btc_in_other_currency = amount
    else:
        btc_in_other_currency = amount / (get_btc_to_currency(currency_code)) 

    logger.info("btc in cad is",btc_in_cad)
    logger.info("btc in other currency is",btc_in_other_currency)

    if btc_in_other_currency < btc_in_cad:
        return True
    else:
        return False



def set_rippling():

    issuing_wallet = CentralWallet.objects.filter(active=True).first().wallet


    if settings.TEST_ENV:
        secret = issuing_wallet.master_seed
    else:
        secret = issuing_wallet.master_key

    account_id = issuing_wallet.account_id

    sequence_number = get_sequence_number(account_id)
    lastledgersequence = get_lastledgersequence()
    lastledgersequence += 4
    logger.info("lastledgersequence is ",lastledgersequence)
    logger.info("sequence_number in @273 is",sequence_number)
    tx_json = {
                "Account": account_id,
                "Fee": "15000",
                "Flags": 0,
                "SetFlag": 8,
                "TransactionType": "AccountSet",
                "Sequence":sequence_number,
                "LastLedgerSequence":lastledgersequence,
            }
    response_dict = sign_and_submit_transaction(tx_json,secret)
    logger.info("response dict after rippling set is",response_dict)

    return response_dict


def disable_account(address,secret_key):
    sequence_number = get_sequence_number(address)
    issuer_wallet=CentralWallet.objects.all().first()

    tx_json = {
                "Account": address,
                "Fee": "5000000",
                "Flags": 2147483648,
                # "Destination": "rLrvrCp81FgDSM6SCXX8rAEJK5qX8BWFMb",
                "Destination": issuer_wallet.wallet.account_id,
                "TransactionType": "AccountDelete",
                "Sequence":sequence_number,
               
            }

    response_dict = sign_and_submit_transaction(tx_json,secret_key)
    logger.info("response dict after rippling set is",response_dict)

    return response_dict
