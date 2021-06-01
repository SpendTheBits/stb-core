from xrpl_wallet.bitgo_utils import get_maximum_spendable
from xrpl_wallet.models import (STBTransaction,AppConfiguration,
        BitcoinWalletAccount,CentralWallet,Currency)
from withdraw.models import  * 

import decimal
from datetime import timedelta,datetime
from django.utils import timezone
import requests
import decimal
from django.utils import timezone
import datetime
from datetime import timedelta
from django.conf import settings
from xrpl_wallet import bitgo_utils
from push_notifications.models import APNSDevice, GCMDevice
import string
import random
from accounts.utils import send_notification

def id_generator(size=8, chars=string.ascii_uppercase+string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def send_btc(amount_in_btc,receiving_address):
    #Returns Success,message, HASH
        logger.info("camein send_btc function to transfer Bitcoins")

        amount_in_satoshi = amount_in_btc * 100000000
        amount_in_satoshi = int(amount_in_satoshi)

        logger.info("amount_in_satoshi is",amount_in_satoshi)

        network_fees_in_btc = calculate_network_fees()

        fee_in_satoshi = network_fees_in_btc * 100000000
        fee_in_satoshi = int(fee_in_satoshi)
        logger.info("fee_in_satoshi is",fee_in_satoshi)
        recipients = {receiving_address:amount_in_satoshi}
        logger.info("recipients is",recipients)
        return bitgo_utils.withdraw(receiving_address,amount_in_satoshi,fee_in_satoshi)


def withdraw_btc_from_main_wallet(transaction_obj):
    

    logger.info("came in withdraw_btc_from_main_wallet")
    
    if transaction_obj.tx_hash_btc is not None:
        return 
    
    amount_in_btc = transaction_obj.value_in_btc
    # logger.info("Ad")
    # network_fees_in_btc = transaction_obj.network_fees_in_btc


    
    receiving_address = transaction_obj.receiving_address
    logger.info("receiving_address is",receiving_address)

 
    central_wallet = CentralWallet.objects.filter(active=True).first().wallet
    central_user = central_wallet.user


    is_success,message,tx = send_btc(amount_in_btc,receiving_address)

    if(is_success):
        try:
            tx_hash=tx['txid']
            logger.info("tx_hash is",tx_hash)
            transaction_obj.tx_hash_btc = tx_hash

            fee_satoshi=float(tx['transfer']['feeString'])
            transaction_obj.network_fees_in_btc =fee_satoshi * 0.00000001
            transaction_obj.save()
            sender_user = transaction_obj.sender.user
            particulars = 'Withdrawn from  {}'.format(sender_user)

            logger.info("particulars is",particulars)
            final_amount_in_btc = amount_in_btc + transaction_obj.network_fees_in_btc

            BitcoinNetworkLedger.objects.create(receiving_address=receiving_address,sender_user=central_user,
                amount=-final_amount_in_btc,notes="WITHDRAW",particulars=particulars,
                reference_number = transaction_obj.reference_number)
        except Exception as e:
            #TODO : SEND FAILURE NOTIFICATION
            transaction_obj.status="failed"
            transaction_obj.error_message= str(e)
            transaction_obj.save()

    else:
        #TODO : SEND FAILURE NOTIFICATION
        transaction_obj.status="failed"
        transaction_obj.error_message= message
        transaction_obj.save()




    return


def send_btc_to_cold_wallet():
    #TODO : To implement this
    return

def check_if_more_than_withdrawal_limit(amount_in_btc):
    #TODO : CONVERT TO BITGO
    logger.info("came in check_if_more_than_withdrawal_limit")
    logger.info("amount_in_btc in check_if_more_than_withdrawal_limit is",amount_in_btc)

    limit_in_btc = WithdrawLimit.objects.filter(active=True).first().limit_in_btc
    logger.info("limit_in_btc is",limit_in_btc)
   
    if amount_in_btc > limit_in_btc:
        return True
    else:
        return False


    


def calculate_network_fees():
    logger.info("came in calculate_network_fees ")
    network_fees_object = NetworkFees.objects.filter(active=True).first()
    
    satoshi_per_byte = network_fees_object.satoshi_per_bytes_for_withdraw_transaction
    transaction_size_in_bytes = network_fees_object.transaction_size_in_bytes_for_withdraw_transaction

    network_fees_in_satoshi = satoshi_per_byte * transaction_size_in_bytes
    network_fees_in_btc = network_fees_in_satoshi / 100000000
    network_fees_in_btc = decimal.Decimal(str(network_fees_in_btc))


    return network_fees_in_btc



def calculate_network_fees_for_fund():
    logger.info("came in calculate_network_fees ")
    network_fees_object = NetworkFees.objects.filter(active=True).first()
    
    satoshi_per_byte = network_fees_object.satoshi_per_bytes_for_fund_transaction
    transaction_size_in_bytes = network_fees_object.transaction_size_in_bytes_for_fund_transaction

    network_fees_in_satoshi = satoshi_per_byte * transaction_size_in_bytes
    network_fees_in_btc = network_fees_in_satoshi / 100000000
    network_fees_in_btc = decimal.Decimal(str(network_fees_in_btc))


    return network_fees_in_btc


def check_if_amount_more_than_spendable_balance(amount_in_btc):
    #TODO : CONVERT TO BITGO
    withdraw_amt_in_satoshi =amount_in_btc* 100000000
    balance_in_satoshi = get_maximum_spendable()
    logger.info("Spendable Balance:",balance_in_satoshi,"Withdraw AMount",withdraw_amt_in_satoshi)
    if balance_in_satoshi - withdraw_amt_in_satoshi <=0:
        return True
    else:
        return False