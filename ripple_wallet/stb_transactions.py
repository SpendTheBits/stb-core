from ripple_wallet.models import *
from ripple_wallet.ripple_utils import get_lastledgersequence,get_sequence_number,update_ripple_account
from ripple_wallet.submit_tx import sign_and_submit_transaction,sign_tx_json,submit_transaction
from ripple_wallet.funding_transactions import (set_ripple_wallet_to_receive_funds,
    update_all_ripple_accounts)
import decimal
import threading
import time
from accounts.models import UserProfile
from accounts.utils import send_notification
from django.conf import settings
from .admin_notifications import related_transaction_transfer_failed_email
from withdraw.models import Ledger
import threading

def create_transaction_object(sender,receiver,amount_in_btc,wallet_activation_charge_in_btc,commission_in_btc):
    """
    1. creation of NORMAL transaction object with value amount_in_btc 

    2. creation of COMMISION trans. object with value commission_in_btc calculated using 
        get_transaction_commission())  and NORMAL transaction object as related transaction,
        here receiver is commission_wallet

    3. if receiver not funded creation of ACTIVATION trans. object with value
        wallet_activation_charge_in_btc and NORMAL trans, obj. as related transaction,
        here receiver is central wallet

    """
    logger.info("came in create_transaction_object")    
    central_wallet = CentralWallet.objects.filter(active=True).first().wallet
    commission_wallet = CommissionWallet.objects.filter(active=True).first().wallet
    
    logger.info("commission_in_btc is",commission_in_btc)
    commission_in_cad = Currency.get_equivalent_amount_in_cad(commission_in_btc,"BTC")
    logger.info("commission_in_cad is",commission_in_cad)



 
    amount_in_cad = Currency.get_equivalent_amount_in_cad(amount_in_btc,"BTC")
    logger.info("amount_in_cad is ",amount_in_cad)
    


    normal_transaction_obj = STBTransaction.objects.create(sender=sender,
        receiver=receiver,value = amount_in_btc,transaction_type="NORMAL",
        value_in_cad=amount_in_cad,wallet_activation_charge=wallet_activation_charge_in_btc)

  

    
    commision_transaction_obj = STBTransaction.objects.create(sender=sender,
        receiver=commission_wallet,value = commission_in_btc,transaction_type="COMMISION",
        value_in_cad=commission_in_cad,related_transaction=normal_transaction_obj)




    if receiver.is_funded is False:
        wallet_activation_charge_in_cad = Currency.get_equivalent_amount_in_cad(
            wallet_activation_charge_in_btc,"BTC")

        logger.info("wallet_activation_charge_in_cad is",wallet_activation_charge_in_cad)  

        activation_stb_obj = STBTransaction.objects.create(sender=sender,
            receiver = central_wallet,value = wallet_activation_charge_in_btc,
            transaction_type="ACTIVATION",value_in_cad=wallet_activation_charge_in_cad,
            related_transaction=normal_transaction_obj)


    return normal_transaction_obj



def create_ledger_entry(transaction_object):
    """
    1. only entry for wallet to wallet type transactions
    2. For each transaction 2 entry
        a. positive amount for receiver
        b. negative amount for sender
    3. based on transaction type send_entry_particulars and receive_entry_particulars is entered


    """
    logger.info("came in create_ledger_entry")
    transaction_type = transaction_object.transaction_type
    sender_user = transaction_object.sender.user
    receiver_user = transaction_object.receiver.user
    amount = transaction_object.value
    currency = "BTC"
    
    logger.info("transaction_type in createledger is",transaction_type)
    if transaction_type=='NORMAL':
        reference_number = transaction_object.reference_number
        send_entry_particulars = "Transferred to {}".format(receiver_user)
        receive_entry_particulars = "Received from {}".format(sender_user)
        notes = "STB Transaction"


    if transaction_type=='COMMISION':
        reference_number = transaction_object.related_transaction.reference_number
        amount_in_btc = transaction_object.related_transaction.value
        send_entry_particulars = "Commission for STB Transaction from {}".format(sender_user)
        receive_entry_particulars = "Commission from {} for {} BTC".format(sender_user,amount_in_btc)
        notes = "Commission Transaction"

    if transaction_type=='ACTIVATION':
        reference_number = transaction_object.related_transaction.reference_number
        amount_in_btc = transaction_object.related_transaction.value
        rcvr = transaction_object.related_transaction.receiver.user
        send_entry_particulars = "Deducted for 20xrp activation fee"
        receive_entry_particulars = "Added BTC for 20xrp given for {}'s activation".format(rcvr)
        notes = "ACTIVATION Transaction"


    if transaction_type=='WTC':
        logger.info("came in @118 WTC")
        reference_number = transaction_object.related_transaction.reference_number
        amount_in_btc = transaction_object.related_transaction.value
        rcvr = transaction_object.related_transaction.receiver.user
        send_entry_particulars = "Deducted {} btc from {} for transferring to cental wallet as {}'s trust line not set".format(
            amount_in_btc,sender_user,rcvr)
        receive_entry_particulars = "Received from {} for transferring to  {} ".format(sender_user,rcvr)
        notes = "STB Transaction"



    if transaction_type=='CTW':
        logger.info("caem in @129 CTW")
        reference_number = transaction_object.related_transaction.reference_number
        amount_in_btc = transaction_object.related_transaction.value
        sndr = transaction_object.related_transaction.sender.user
        send_entry_particulars = "Send from central wallet as  {}'s trust line is set ".format(
            receiver_user)
        receive_entry_particulars = "Received {} BTC from central wallet for STB transaction from {}".format( 
            amount_in_btc,sndr)
        notes = "STB Transaction"

    if transaction_type=='FUNDWALLET':
        related_funding_transaction = transaction_object.related_funding_transaction
        
        stb_reference_number = transaction_object.reference_number       
        reference_number = transaction_object.related_funding_transaction.reference_number       
        send_entry_particulars = "Issued to {} for Fund Transaction with STB ref no.  {}".format(
            receiver_user,stb_reference_number)
        receive_entry_particulars = "Issued from central wallet for Fund Transaction with STB ref no {}".format(
            stb_reference_number)
        notes = "FundWallet Transaction"


    if transaction_type=='WITHDRAWAL':
        logger.info("came in WITHDRAWAL")
        withdrawal_transaction = transaction_object.withdrawal_transaction.all().first()    
        withdrawal_reference_number =  withdrawal_transaction.reference_number  
        network_fees_in_btc =  withdrawal_transaction.network_fees_in_btc
        reference_number = transaction_object.reference_number 
        send_entry_particulars = "Deducted for withdrawal with ref no {}".format(withdrawal_reference_number)
        receive_entry_particulars = "Received for withdrawal from {}".format(sender_user)
        notes = "Withdrawal Transaction"

    if transaction_type=='REFUND WITHDRAWAL':
        logger.info("@160 refund")
        if transaction_object.refund_withdrawal_transaction.all().exists():
            withdrawal_transaction = transaction_object.refund_withdrawal_transaction.all().first()   
            withdrawal_reference_number = withdrawal_transaction.reference_number        
            reference_number = transaction_object.reference_number     
            send_entry_particulars = "Refunded as withdrawal request for {} denied".format(withdrawal_reference_number)
            receive_entry_particulars = send_entry_particulars
        else:
            reference_number = transaction_object.related_transaction.reference_number
        notes = "REFUND WITHDRAWAL"

    if transaction_type=='REFUND COMMISION':
        logger.info("@1730 refund commission")
     
        reference_number = transaction_object.related_transaction.reference_number     
        send_entry_particulars = "Refunded as Commission transaction failed for {}".format(reference_number)
        receive_entry_particulars = send_entry_particulars

        notes = "REFUND COMMISION"


    if transaction_type=='REFUND ACTIVATION':
        logger.info("@1830 refund activation")      
        reference_number = transaction_object.related_transaction.reference_number    
        send_entry_particulars = "Refunded as Activation transaction failed for {}".format(reference_number)
        receive_entry_particulars = send_entry_particulars
        notes = "REFUND ACTIVATION"






    send_entry_ledger = Ledger.objects.create(user=sender_user,particulars=send_entry_particulars,
        currency=currency,amount=-amount,notes=notes,reference_number=reference_number)

    receive_entry_ledger = Ledger.objects.create(user=receiver_user,particulars=receive_entry_particulars,
        currency=currency,amount=amount,notes=notes,reference_number=reference_number)

    logger.info("ledget entry is created")
    return


def process_transaction_result(response_dict,transaction_id):
    """
    1.response_dict from sign_and_submit_transaction is used and trasnaction object.tx_hash is updated

    2.if no error occured then transaction status is updated as successful
        a.create_ledger_entry() is called
        b.
    

    3. if error occured then transaction status is updated as failed and if 

    """

    logger.info("came in process_transaction_result")
    transaction_object = STBTransaction.objects.get(id=transaction_id)

    receiver = transaction_object.receiver
    sender = transaction_object.sender
    sender_addr = sender.account_id
    receiver_addr = receiver.account_id

    tx_hash = response_dict['tx_hash']
    validated = response_dict['validated']
    error = response_dict['error']
    engine_result = response_dict['engine_result']
    engine_result_message = response_dict['engine_result_message']

    transaction_object.is_validated = validated
    transaction_object.tx_hash = tx_hash
    logger.info("error is",error)
    logger.info("hash in process transaction result is",tx_hash)
    if error is True:
        transaction_object.status = "failed"
        transaction_object.error_code = engine_result
        transaction_object.error_message = engine_result_message
        transaction_type = transaction_object.transaction_type
        logger.info("transaction_type is",transaction_type)
        if  transaction_type == "WTC" or transaction_type == "CTW":
            main_transaction = transaction_object.related_transaction
            logger.info("main_transaction is",main_transaction.id)
            main_transaction.status = "failed"
            main_transaction.is_validated = validated
            main_transaction.error_code = engine_result
            main_transaction.error_message = engine_result_message
            main_transaction.tx_hash = tx_hash
            main_transaction.save()

    else:
        logger.info("transaction successful")
        transaction_object.status = "successful"
        transaction_object.error_code = None
        transaction_object.error_message = None

        #ledger entry
        create_ledger_entry(transaction_object)
        
        logger.info("caem after create_ledger_entry")
        #sending notification

        transaction_type = transaction_object.transaction_type
        if transaction_type == "CTW" or transaction_type == "NORMAL":
            receiving_amount = transaction_object.value
            if transaction_type == "CTW":

                main_transaction = transaction_object.related_transaction
                sender_user  = main_transaction.sender.user               
                main_transaction.status = "successful"
                main_transaction.is_validated = validated
                main_transaction.tx_hash = tx_hash
                main_transaction.save()
                reference_no = main_transaction.reference_number
            else:
                sender_user = transaction_object.sender.user
                reference_no = transaction_object.reference_number

            sender_username = sender_user.username
            receiver_user = receiver.user
            message = "Received {} BTC from {}".format(receiving_amount,sender_username)            
            sender_message = "Transaction {} is successful".format(reference_no)
            response = send_notification(receiver_user,message)            
            response2 = send_notification(sender_user,sender_message)
           


    transaction_object.save()

    #updating sender and receiver balances
    logger.info("updating sender addr@263")
    x = update_ripple_account(sender_addr)
    logger.info("updating receive addr")
    y = update_ripple_account(receiver_addr)


    return



def create_iou_payment_transaction_json(sender_addr,receiver_addr,bitcoin_amount,transaction_id):
    transaction_object = STBTransaction.objects.get(id=transaction_id)
    logger.info("sender is",sender_addr)
    logger.info("receiver is",receiver_addr)
    logger.info("@349")
    logger.info("bitcoin amount is",bitcoin_amount)
    logger.info("transaction_id is",transaction_id)
    # value must be str so bitcoin amount has to be made into str
    bitcoin_amount = str(bitcoin_amount)
    logger.info("bitcoin_amount in str is @353",bitcoin_amount)


    # if settings.PRODUCTION_ENV:

    #     stb_wallet = RippleWallet.objects.get(account_id=sender_addr)
    #     sequence_number = stb_wallet.current_sequence_number
    #     if sequence_number is None:
    #         sequence_number = get_sequence_number(sender_addr)

    #     stb_wallet.current_sequence_number = sequence_number + 1
    #     stb_wallet.save()
    # else:
    #     sequence_number = get_sequence_number(sender_addr)
        
    sequence_number = get_sequence_number(sender_addr)

    logger.info("sequence number in @44 is",sequence_number)
    # sequence_number_error = True
    # while sequence_number_error is True:



    transaction_object.sequence = str(sequence_number)
    lastledgersequence = get_lastledgersequence()
    lastledgersequence += 4
    transaction_object.last_ledger_sequence = lastledgersequence
    transaction_object.save()
    logger.info("lastledgersequence is ",lastledgersequence)
    logger.info("seqnuce number is ",sequence_number)

    stb_issuer_wallet = CentralWallet.objects.filter(active=True).first().wallet
    issuer = stb_issuer_wallet.account_id
    if settings.TEST_ENV:
        currency_code = "BTC"


    else:

        # currency_code = "BTC"
        # stb_issuer_wallet = CentralWallet.objects.filter(active=True).first().wallet
        # issuer = stb_issuer_wallet.account_id

        currency_code = "BTC"
        # issuer = "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B"

    logger.info("currency code in stb to stb is",currency_code)
    logger.info(" issuer in stb to stb is",issuer)
    tx_json = {
            "Account": sender_addr,
            "Amount" : {
                "currency" : currency_code,
                "value" : bitcoin_amount,
                "issuer" : issuer
            },
            "LastLedgerSequence":lastledgersequence,
            "Destination": receiver_addr,
            "TransactionType": "Payment",
            "Fee":50,
            "Sequence":sequence_number,
            "Flags":131072

        }

    return tx_json




def stb_to_stb_transfer(sender_addr,receiver_addr,bitcoin_amount,secret_key,transaction_id):
    """
    1. creation of tx_json dictionary from create_iou_payment_transaction_json()

    2. submitting tx_json and secretkey in sign_and_submit_transaction()

    3. if error occured(not from xrpl but due to code) transaction status is updated as failed

    4. if no error then process_transaction_result() with response_dict from sign_and_submit_transaction

    """
    transaction_object = STBTransaction.objects.get(id=transaction_id)
    logger.info("transaction_object is  is",transaction_object.id)
    tx_json = create_iou_payment_transaction_json(sender_addr,receiver_addr,bitcoin_amount,transaction_id)
    logger.info("tx_json is",tx_json)
    
    secret = secret_key
    try:
        response_dict = sign_and_submit_transaction(tx_json,secret)
    except  Exception as e:
        logger.info("error in submitting stb_to_stb_transfer transaction is",e)
        transaction_object.is_validated = False
        transaction_object.status = "failed"
        transaction_object.error_message = str(e)
        transaction_object.save()
        response_dict = dict()

        response_dict['validated'] = False
        response_dict['engine_result'] = ''
        response_dict['error'] = True
        response_dict['engine_result_message'] = str(e)
        logger.info("response_dict @198 in stb",response_dict)
        return response_dict


    logger.info("response_dict of sign_and_submit_transaction  in stb_to_stb_transfer is ",sign_and_submit_transaction)
    logger.info("@354 before process_transaction_result")
    response = process_transaction_result(response_dict,transaction_id)
    logger.info("@356 after process_transaction_result")
    return response_dict



def create_transfer(transaction_id,secret_key=None):
    """
    stb_to_stb_transfer() function is called and response dict is returned
    """

    logger.info("came in create transfer")
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

    logger.info("create_transfer is done")
    logger.info('response_dict in create_transfer is',response_dict)
    return response_dict



def create_related_transaction_transfer(related_transaction_obj,secret_key):
    logger.info("came in create_related_transaction_transfer ")    
    response_dict = create_transfer(related_transaction_obj.id,secret_key)
    
    error = response_dict['error']
    if error is True:
        logger.info("@393 error is True")

        related_transaction_transfer_failed_email(related_transaction_obj)  

    return response_dict

def handle_commission_and_activation_fee_transfer(stb_transaction_object,secret_key):
    logger.info("came in handle_commission_and_activation_fee_transfer")
    error_response = False
    commission_transaction_list = stb_transaction_object.related_transactions.filter(transaction_type="COMMISION")
    fundwallet_transaction_list = stb_transaction_object.related_transactions.filter(transaction_type="ACTIVATION")


    for commission_object in commission_transaction_list:
        response_dict = create_related_transaction_transfer(commission_object,secret_key)

        error = response_dict['error']
        if error is True:
            error_response = True
            return error_response
    logger.info("comsssion transfer handled")

    for fund_wallet_transaction_object in fundwallet_transaction_list:

        response_dict = create_related_transaction_transfer(fund_wallet_transaction_object,secret_key)
        error = response_dict['error']
        if error is True:
            error_response = True
            return error_response


    logger.info("activation fee transfer handled")


    return



def create_pending_transaction(normal_transaction_object,secret_key):
    logger.info("create_pending_transaction with ")

    cpt_response = {'error':False}
    
   
    central_wallet = CentralWallet.objects.filter(active=True).first().wallet
    bitcoin_amount = normal_transaction_object.value
    value_in_cad = normal_transaction_object.value_in_cad
    

    receiver = normal_transaction_object.receiver
    sender = normal_transaction_object.sender
    sender_addr = sender.account_id


    transaction_type="WTC"


    wtc_transaction_obj = STBTransaction.objects.create(sender=sender,
    receiver=central_wallet,value = bitcoin_amount,transaction_type=transaction_type,
    related_transaction=normal_transaction_object,value_in_cad=value_in_cad,is_otp_verfied=True)    
    
    response_dict = create_transfer(wtc_transaction_obj.id,secret_key)
    logger.info("create_transfer in create_pending_transaction done ")
    error = response_dict['error']

    logger.info("error is@448",error)

    if error is True:

        cpt_response = {'error':True}

        return cpt_response
    

    pending_transaction_obj = PendingTransactions.objects.create(receiver=receiver,
    transaction_id=normal_transaction_object.id,sender=sender)

    logger.info("create_pending_transaction is done")
    return cpt_response




def initiate_related_transaction_refund(normal_transaction_object):
    central_wallet = CentralWallet.objects.filter(active=True).first().wallet
    receiver = normal_transaction_object.receiver

    if settings.TEST_ENV:
        secret_key = central_wallet.master_seed
    else:        
        secret_key = central_wallet.master_key

    commission_transaction_list = normal_transaction_object.related_transactions.filter(
        transaction_type="COMMISION",status="successful")
    fundwallet_transaction_list = normal_transaction_object.related_transactions.filter(
        transaction_type="ACTIVATION",status = "successful")

    transaction_type = 'REFUND COMMISION'

    for commission_transaction in commission_transaction_list:
        bitcoin_amount = commission_transaction.value
        value_in_cad = commission_transaction.value_in_cad        
        refund_transaction_obj = STBTransaction.objects.create(sender=central_wallet,
            receiver=receiver,value = bitcoin_amount,transaction_type=transaction_type,
            related_transaction=normal_transaction_object,value_in_cad=value_in_cad,
            is_otp_verfied=True)
        response_dict = create_transfer(refund_transaction_obj.id,secret_key)
        error = response_dict['error']
        if error is True:
            related_transaction_transfer_failed_email(commission_transaction)

    transaction_type = 'REFUND ACTIVATION'

    for activation_transaction in fundwallet_transaction_list:
        bitcoin_amount = activation_transaction.value
        value_in_cad = activation_transaction.value_in_cad        
        refund_transaction_obj = STBTransaction.objects.create(sender=central_wallet,
            receiver=receiver,value = bitcoin_amount,transaction_type=transaction_type,
            related_transaction=normal_transaction_object,value_in_cad=value_in_cad,
            is_otp_verfied=True)
        response_dict = create_transfer(refund_transaction_obj.id,secret_key)
        error = response_dict['error']
        if error is True:
            related_transaction_transfer_failed_email(activation_transaction)

    
    return


def update_related_transaction_as_failed(stb_transaction_object):
    related_transaction_list = stb_transaction_object.related_transactions.all()

    for related_transaction in related_transaction_list:
        related_transaction.status = 'failed'
        related_transaction.error_message = "Main transaction failed"
        related_transaction.save()

    return


def initiate_transaction(transaction_id,secret_key):
    """
    1. firstly checks if is_trust_line_set or not

    2. if trustline is set create_transfer() is called
        a. if sucessfull handle_commission_and_activation_fee_transfer() is called
        b. if failed update_related_transaction_as_failed() is called

    """
    logger.info("came in intaite transction")
    try:
        normal_transaction_object = STBTransaction.objects.get(id =transaction_id)
        
        receiver = normal_transaction_object.receiver
        sender = normal_transaction_object.sender
        receiver_address = receiver.account_id


        error_res = handle_commission_and_activation_fee_transfer(normal_transaction_object,secret_key)

        logger.info("error_res is",error_res)

        if error_res is True:
            update_related_transaction_as_failed(normal_transaction_object)
            # initiate_related_transaction_refund(normal_transaction_object)
            return        
        logger.info("receiver.is_trust_line_set is ",receiver.is_trust_line_set)




        if receiver.is_trust_line_set is False:
            logger.info("trust line not set")
            cpt_response = create_pending_transaction(normal_transaction_object,secret_key)
            cpt_error = cpt_response['error']
            logger.info("cpt error is ",cpt_error)

            if cpt_error is True:
                update_related_transaction_as_failed(normal_transaction_object)
                # initiate_related_transaction_refund(normal_transaction_object)
                return
            logger.info("created create_pending_transaction for main  ")
            

            if receiver.is_funded is False:
                # very first payment received by receiver so not funded

                logger.info("not funded")
                try:
                    response_dict = set_ripple_wallet_to_receive_funds(
                        receiver_address,'activation_through_wallet',normal_transaction_object.id)
                except  Exception as e:
                    logger.info("error in submitting transaction is @466",e)
                    normal_transaction_object.is_validated = False
                    normal_transaction_object.status = "failed"
                    normal_transaction_object.error_message = str(e)
                    normal_transaction_object.save()

                    #updating status of related transaction as main transaction failed
                    update_related_transaction_as_failed(normal_transaction_object)
                    # initiate_related_transaction_refund(normal_transaction_object)
                    return
                error = response_dict['error']
                if error is True:
                    #set_ripple_wallet_to_receive_funds failed
                    logger.info("set_ripple_wallet_to_receive_funds failed")

                    #updating status of related transaction as main transaction failed
                    update_related_transaction_as_failed(normal_transaction_object)
                    # initiate_related_transaction_refund(normal_transaction_object)

                    return
    except Exception as e:
        logger.info("Error in initoate transaction",str(e))
        return



    #trust lines already set so normal flow
    response_dict = create_transfer(normal_transaction_object.id,secret_key)
    error = response_dict['error']
    if error is True:
        #updating status of related transaction as main transaction failed
        update_related_transaction_as_failed(normal_transaction_object)
        return

    
    # handle_commission_and_activation_fee_transfer(normal_transaction_object,secret_key)
      

    return 



def xrp_transfer(sender_addr,receiver_addr,secret_key,amount):






    amount = int(amount) * 1000000
    amount = str(amount)
    logger.info("amount in xrp transfer is",amount)
    logger.info("sender address is ",sender_addr)

    sequence_number = get_sequence_number(sender_addr)
    logger.info("sequqnece number us",sequence_number)

    lastledgersequence = get_lastledgersequence()
    lastledgersequence += 4
    secret = secret_key
    tx_json = {
            "Account": sender_addr,
            "Amount" : amount,
            "LastLedgerSequence":lastledgersequence,
            "Destination": receiver_addr,
            "TransactionType": "Payment",
            "Fee":5000,
            "Sequence":sequence_number,


        }

    try:
        response_dict = sign_and_submit_transaction(tx_json,secret)
    except  Exception as e:
        logger.info("error in submitting  xrp_transfer transaction is",e)
        response_dict = dict()

        response_dict['validated'] = False
        response_dict['engine_result'] = ''
        response_dict['error'] = True
        response_dict['engine_result_message'] = str(e)
        return response_dict
    logger.info("response dict is",response_dict)


    #updating sender and receiver balances
    logger.info("updating sender addr")
    x = update_ripple_account(sender_addr)
    logger.info("updating receive addr")
    y = update_ripple_account(receiver_addr)
    logger.info("sending response dict")
    return response_dict




def issue_btc_to_stb_wallet(customer_address,bitcoin_amount,funding_transn_obj):
    # user = request.user
    logger.info("@issue_btc_to_stb_wallet")
    logger.info("bitcoin amount is",bitcoin_amount)

    central_wallet = CentralWallet.objects.filter(active=True).first().wallet
    receiver = RippleWallet.objects.get(account_id=customer_address)
    
    if settings.TEST_ENV:
        secret_key = central_wallet.master_seed
    else:        
        secret_key = central_wallet.master_key
      
    value_in_cad = Currency.get_equivalent_amount_in_cad(bitcoin_amount,"BTC")
    logger.info("value_in_cad in issue_btc_to_stb_wallet is",value_in_cad)
    transaction_type="FUNDWALLET"

    fundwallet_stb_transaction_obj = STBTransaction.objects.create(sender=central_wallet,
        receiver=receiver,value = bitcoin_amount,transaction_type=transaction_type,
        related_funding_transaction=funding_transn_obj,
        value_in_cad=value_in_cad,is_otp_verfied=True)    


    update_reference_no_for_stb_transaction(fundwallet_stb_transaction_obj)


    response_dict = create_transfer(fundwallet_stb_transaction_obj.id,secret_key)
 
    error = response_dict['error']
    if error is True:
        funding_transn_obj.is_error_occurred = True                
        funding_transn_obj.status = 'failed'
        funding_transn_obj.error_tx_hash = response_dict['tx_hash']
        funding_transn_obj.error_message = response_dict['engine_result_message']
        funding_transn_obj.error_code = response_dict['engine_result']
        funding_transn_obj.save()


        # issue_btc_to_stb_wallet_failed(fund_transaction_obj,stb_transaction_obj)
        return response_dict

    funding_transn_obj.is_error_occurred = False
    funding_transn_obj.status = 'successful'
    funding_transn_obj.save()

    message = "Your wallet has been funded with {} btc".format(bitcoin_amount)
    send_notification(receiver.user,message)



    #updating all ripple accounts ripple as well as bitcoin balance

    thread1 = threading.Thread(target=update_all_ripple_accounts, args=())
    # try:
    #     result = update_all_ripple_accounts()
    # except Exception as e:
    #     logger.info("error in updating ripple accounts is",e)
    return response_dict



def update_reference_no_for_stb_transaction(stb_transaction_object):

    app_config_obj = AppConfiguration.objects.filter(active=True).first()
    current_reference_number = app_config_obj.current_reference_number

    if current_reference_number is None:
        new_refernce_no = "STB1000001"
    else:
        new_refernce_no = current_reference_number[:3]+str(int(current_reference_number[3:])+1)

    stb_transaction_object.reference_number = new_refernce_no
    stb_transaction_object.save()

    app_config_obj.current_reference_number = new_refernce_no
    app_config_obj.save()

    return


def update_otp_status_and_ref_no_for_stb_transaction(stb_transaction_object,ip):


    update_reference_no_for_stb_transaction(stb_transaction_object)

    stb_transaction_object.is_otp_verfied = True
    stb_transaction_object.ip_address = ip
    stb_transaction_object.save()


    related_transaction_list = stb_transaction_object.related_transactions.all()

    for related_transaction in related_transaction_list:
        related_transaction.is_otp_verfied = True
        related_transaction.ip_address = ip
        related_transaction.save()

    return