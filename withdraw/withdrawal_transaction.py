from xrpl_wallet.models import *
from withdraw.models import  * 
from xrpl_wallet.models import CentralWallet,STBTransaction 
from xrpl_wallet.stb_transactions import (create_transfer,stb_to_stb_transfer,
    update_reference_no_for_stb_transaction)
from withdraw.utils import withdraw_btc_from_main_wallet,calculate_network_fees_for_fund,send_btc
from accounts.utils import send_notification
from django.conf import settings
from xrpl_wallet.admin_notifications import withdraw_transaction_request_admin_mail
from xrpl_wallet.bitgo_utils import update_bitcoin_balance


def create_withdraw_transaction_object(sender,receiver_address,bitcoin_amount,network_fees_in_btc):
    logger.info("came in create_withdraw_transaction_object")

    final_bitcoin_amount = bitcoin_amount + network_fees_in_btc
    central_wallet = CentralWallet.objects.filter(active=True).first().wallet
    bitcoin_amount_in_cad = Currency.get_equivalent_amount_in_cad(bitcoin_amount,"BTC")
    final_bitcoin_amount_in_cad = Currency.get_equivalent_amount_in_cad(final_bitcoin_amount,"BTC")
    
    
    logger.info("bitcoin_amount_in_cad is",bitcoin_amount_in_cad)

    related_transaction_obj = STBTransaction.objects.create(sender=sender,
        receiver=central_wallet,value = final_bitcoin_amount,transaction_type="WITHDRAWAL",
        value_in_cad=final_bitcoin_amount_in_cad)


    withdraw_transaction_object = WithDrawalTransaction.objects.create(sender=sender,
        receiving_address=receiver_address,value_in_btc = bitcoin_amount,
        related_transaction=related_transaction_obj,value_in_cad=bitcoin_amount_in_cad,
        network_fees_in_btc=network_fees_in_btc,transaction_type="NORMAL")

    return withdraw_transaction_object


def create_withdraw_stb_transfer(transaction_id,secret_key=None):

    logger.info("came in create create_withdraw_stb_transfer transfer")
    logger.info("transaction id is",transaction_id)
    stb_transaction_object = STBTransaction.objects.get(id =transaction_id)
    receiver = stb_transaction_object.receiver
    sender = stb_transaction_object.sender
    bitcoin_amount = stb_transaction_object.value
    sender_addr = sender.account_id
    receiver_addr = receiver.account_id

    sequence_error = True
    while (sequence_error==True):
        response_dict = stb_to_stb_transfer(sender_addr,receiver_addr,
        bitcoin_amount,secret_key,transaction_id)
        if response_dict['engine_result']!='tefPAST_SEQ':
            sequence_error = False

    logger.info("came in create create_withdraw_stb_transfer ended")
    return response_dict

def create_refund_stb_transfer(withdraw_transaction_object):

    #TODO : To implement this
    return None


def initiate_withdraw_transaction(transaction_id,secret_key):
    logger.info("came in intaite transction.THis function is called too PROCESS the withdraw transaction after all checks and OTP")
    #TODO : To implement this
    return 




def time_left_before_allowing_transaction_blocked_due_to_withrawal(user):
    #TODO : To implement this
    return 0



def approve_withdrawal_transaction(withdrawal_transaction_obj):
    #TODO : To implement this
    return


def decline_withdrawal_transaction(withdrawal_transaction_obj):
    #TODO : To implement this
    return



def update_otp_status_and_ref_no_for_withdraw_transaction(withdraw_transaction_object,ip):
    #TODO : To implement this
    return 





def send_btc_to_central_wallet(sender_bitcoin_account):
    #TODO : To implement this
    return

     