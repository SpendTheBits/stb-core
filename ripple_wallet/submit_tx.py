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
from ripple_wallet.ripple_utils import *
from django.conf import settings
def submit_transaction(tx_blob):
    logger.info("came in  submit transction")
    #to submit a transaction, we sign it using sign_transaction and serialize it using serailize_object,
    #and use submit method of ripple to submit the transaction


    # result_after_sign = sign_transaction(tx_json,secret)

    

    to_send = {
        "method": "submit",
        "params": [
            {
                "tx_blob": tx_blob
            }
        ]
    }
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)

    json_response = response.json()
    logger.info("json response after submit transactini is",json_response)
    tx_hash = json_response['result']['tx_json']['hash']
    sequence_no = json_response['result']['tx_json']['Sequence']
    sender = json_response['result']['tx_json']['Account']
    lastledgersequence = json_response['result']['tx_json']['LastLedgerSequence']
    engine_result = json_response['result']['engine_result']
    engine_result_message = json_response['result']['engine_result_message']
    logger.info("hash is",tx_hash)
    logger.info("sequence_no is",sequence_no)
    logger.info("sender is",sender)
    logger.info("lastledgersequence is",lastledgersequence)
    logger.info("engine_result is",engine_result)
    logger.info("engine_result_message is",engine_result_message)


    response_dict = {
        "error":False,"tx_hash":tx_hash,"engine_result":engine_result,
        "engine_result_message":engine_result_message,"validated":False
    }





    validated = False
    while validated is not True:
        #checking transaction using tx method to check status after 5 seconds of submit method
        #  to let it included in a ledger
        time.sleep(5)
        to_send =  {
            "method": "tx",
            "params": [
                {
                    "transaction": tx_hash,
                    "binary": False,

                }
            ]
        }

        response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)
        json_response = response.json()
        status_code = response.status_code
        result = json_response['result']
        validated = result.get('validated',None)
        logger.info("validated is",validated)

        if validated is True:
            #in both case transactin is validated is true
            logger.info("validation is true so came here")
            response_dict['validated'] = True
            if result['meta']['TransactionResult'] == "tesSUCCESS":
                logger.info("successful ")
            else:
                response_dict['error'] = True
                logger.info("failed")
        else:
            # keep checking till current lastledgersequence is equal to transaction's lastledgersequence
            logger.info("validation is not true here")
            newest_validated_ledger = get_lastledgersequence()
            logger.info("newest_validated_ledger is ",newest_validated_ledger)
            if (lastledgersequence <= newest_validated_ledger):
                logger.info("@429")
                #check if server has conitinous history of (LastLedgerSequence -3) to LastLedgerSequence
                #if the server does not have then wait till it has
                in_ledger_history = ledger_history(lastledgersequence)
                if in_ledger_history is True:
                    logger.info("it tansaction sequence is less")
                    new_sequence_number = get_sequence_number(sender)
                    logger.info("new sequence number is",new_sequence_number)
                    logger.info("sequence number is",sequence_no)
                    if new_sequence_number <= sequence_no:
                        logger.info("Transaction has not been included in any validated ledger andnever will be")
                        response_dict['error'] = True
                        break
                    else:
                        logger.info("A different transaction with this sequence has a final outcome")
                        response_dict['error'] = True
                        response_dict['validated'] = True
                        break


    logger.info("response dict inside sumbit tx is",response_dict)

    return response_dict


def sign_tx_json(tx_json,secret):
    try:
        result_after_sign = sign_transaction(tx_json,secret)
    except:
        logger.info('error in sign_transaction @127')

    logger.info("result after sign is",result_after_sign)
    tx_blob =  serialize_object(result_after_sign)
    return tx_blob

def sign_and_submit_transaction(tx_json,secret):
   
    logger.info("came in sign_and_submit_transaction")
    try:
        result_after_sign = sign_tx_json(tx_json,secret)
    except:
        logger.info('error from calling sign_tx_json method @139')
    logger.info("sign_tx_json done",result_after_sign)
    response_dict = submit_transaction(result_after_sign)
    logger.info("sign_tx_json done in sign_and_submit_transaction",response_dict)
    return response_dict


def single_sign_and_submit_transaction(tx_json,secret):

    result_after_sign = sign_transaction(tx_json,secret)
    # logger.info("result after sign is",result_after_sign)
    tx_blob =  serialize_object(result_after_sign)


    to_send = {
        "method": "submit",
        "params": [
            {
                "tx_blob": tx_blob
            }
        ]
    }
    response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)

    json_response = response.json()

    error = True
    engine_result = json_response['result']['engine_result']
    logger.info("engine_result is",engine_result)
    if engine_result == "tesSUCCESS":
        error = False

    response_dict = {
        "error":error
    }


    return response_dict



def sign_and_hard_submit_transaction(tx_json,secret):
    #to implement in future
    # result_after_sign = sign_tx_json(tx_json,secret)
    # response_dict = submit_transaction(result_after_sign)
    # return response_dict
    return 