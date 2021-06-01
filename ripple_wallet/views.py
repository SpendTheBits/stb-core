from django.shortcuts import render
import os
from accounts.utils import send_mail_for_transaction
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import filters
from django.http import JsonResponse
# from wallet.serializers import *
from ripple_wallet.models import *
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny
from ripple_wallet.serializers import *
import decimal
from NamedAtomicLock import NamedAtomicLock
import json
import requests
from .sign import sign_transaction
from.serialize import serialize_object
import threading
from accounts.models import UserProfile,User
from accounts.utils import  send_notification,get_host_from_url
from datetime import timedelta,datetime
import time
from django.views.decorators.csrf import csrf_exempt
from django.dispatch import receiver

from django.db.models.signals import pre_save,post_save
from ripple_wallet.ripple_utils import (update_all_ripple_accounts,get_btc_from_xrp,
    get_btc_balance_for_ripple_wallet,update_ripple_account,ledger_history,get_lastledgersequence,
    get_sequence_number)

from ripple_wallet.funding_transactions import (set_ripple_wallet_to_receive_funds,
    get_wallet_activation_fee_in_btc,get_btc_to_currency,time_left_before_allowing_transaction,
    transfer_stb_to_wallet,set_trust_lines,set_rippling,request_to_set_trust_lines,
    create_fund_transaction_object,calculate_bitcoin_amount_to_sent)

from ripple_wallet.stb_transactions import  (create_transaction_object,initiate_transaction,
    xrp_transfer,process_transaction_result,create_transfer,update_related_transaction_as_failed,
    issue_btc_to_stb_wallet,update_otp_status_and_ref_no_for_stb_transaction)


from authy.api import AuthyApiClient
from ripple_wallet.submit_tx import submit_transaction
from rest_framework.settings import api_settings
from rest_framework.pagination import PageNumberPagination
from .pagination import PaginationHandlerMixin
authy_api = AuthyApiClient(settings.ACCOUNT_SECURITY_API_KEY)
from django.views.decorators.http import require_http_methods
from twilio.rest import Client
from payid.models import *
from withdraw.models import Ledger,BitcoinNetworkLedger,WithDrawalTransaction
from withdraw.withdrawal_transaction import send_btc_to_central_wallet
# Your Account Sid and Auth Token from twilio.com/console
# DANGER! This is insecure. See http://twil.io/secure
account_sid = settings.TWILIO_ACCOUNT_SID
auth_token = settings.TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)



def get_transaction_details_from_bitgo(body):
    logger.info('In get_transaction_details_from_bitgo=',body)

    #CHECK THE JSON RECD
    try:
        body= json.loads(body)
        transfer_id=body['transfer']
        logger.info("Transfer ID ",transfer_id)
        wallet_id=settings.BITGO_WALLET
        url=settings.BITGO_URL+"/api/v2/"+settings.BITGO_COIN+"/wallet/"+str(wallet_id)+"/transfer/"+str(transfer_id)
        logger.info("Before passtopken")
    except Exception as e:
        logger.info(str(e))
        return None,None,None,None,"Invalid body in request"

    #CHECK IF BITGO KEY IS THERE IN ENV
    try:
        # logger.info("Key",os.environ.get('BITGO_KEY'))
        pass_token={
            "Authorization":'Bearer '+ settings.BITGO_KEY
        }
    except Exception as e:
        logger.info(str(e))
        return None,None,None,None,"Exception in getting Token Bitgo"
    logger.info("Token",pass_token['Authorization'][-5:])

    # GET TRANSFER DETAILS FROM BITGO API
    try:
        response=requests.get(url,headers=pass_token)
        if(response.status_code!=200):
            logger.info("ERROR Code from BITGO",str(response.status_code))
        # printresponse.text
    except Exception as e:
        logger.info('error in getting transfer info ',str(e))
        return None,None,None,None,'ERROR in getting transfer info'

    # GET VALUE AND OTHER DETAILS FROM BITGO
    try:
        transfer_info = response.json()
        logger.info(str(transfer_info))
        valid_add_found=False
        for output in transfer_info['outputs']:
            if 'wallet' in output:
                address = output['address']
                value = output['value']
                valid_add_found = True
                break
        if not valid_add_found:
            return None,None,None,None,'No valid transaction found'
        # address=transfer_info['outputs'][0]['address']
        logger.info("Received funds in this address",address)
        confirmations=transfer_info['confirmations']
        # value=transfer_info['outputs'][0]['value']
        value_in_btc = value / 100000000
        value_in_btc = decimal.Decimal(str(value_in_btc))
        txid=transfer_info['txid']
        return address,txid,value_in_btc,confirmations,None
    except Exception as e:
        logger.info('ERROR',str(e))
        return None,None,None,None,'ERROR in '+str(e)     

@require_http_methods(["POST"])
@csrf_exempt
def notify_bitgo_confirmed(request):
    try:
        address,txid,value_in_btc,confirmations,error =get_transaction_details_from_bitgo(request.body)
        if(error):
            return HttpResponse(str(error),status = 400)
    except:
        return HttpResponse('ERROR in getting Bitgo Details',status=400)
    try:
        bitcoin_address_obj = FundingAddress.objects.get(address=address)
    except Exception as e:
        logger.info('Not found Funding Address with',address)
        return HttpResponse('ERROR in Funduing Address',status=400)


    #Now we have user, address, funds, confirmations
    user = bitcoin_address_obj.bitcoin_account.user
    logger.info("user is",user)
    bitcoin_wallet_account_object = BitcoinWalletAccount.objects.get(user=user)
    app_config_obj = AppConfiguration.objects.filter(active=True).first()
    confirmation_amount_in_btc = app_config_obj.confirmation_amount_in_btc

    if value_in_btc <= confirmation_amount_in_btc:
        confirmation_limit = 1
    else:
        confirmation_limit = 3
    myLock = NamedAtomicLock(txid)
    if myLock.acquire(timeout=5):
        try:#MUTEX KE LIYE YE TRY HAI
            #CREATE / UPDATE FUNDING TRANSACTION
            try:
                toret = False
                fund_object = FundingTransaction.objects.get(tx_hash=txid)
                logger.info("Confirmations ",fund_object.confirmations," vs ",confirmation_limit)
                if(fund_object.confirmations>=confirmation_limit): # MEANS WE HAVE ALREADT ENTERED THIS FUNCTION ONCE
                    toret = True
                fund_object.confirmations = confirmations
                fund_object.save()
                if(toret):
                    return HttpResponse('Just increasing confoirmations')
                # if fund_object.transaction_verfied is True:
                #     return HttpResponse('Just increasing confoirmations')
                # if fund_object.status!='pending'or fund_object.is_ledger_created :
                #     return HttpResponse('Transaction already complete.Just increasing confoirmations')
            except Exception as e:
                logger.info("Exception in get fund tranbsaction",str(e))
                fund_object = create_fund_transaction_object(txid,user,value_in_btc,confirmations)

            if confirmations < confirmation_limit:
                logger.info("@126 confirmation less than confirmation_limit which is now is",confirmation_limit)
                return HttpResponse('OK')

            else: # IF CONFIRMATIONS >= CONFIRMATION LIMIT
                # fund_object.confirm_transaction()#_fund_transaction(fund_object)
                #IF his BTC balance not increased , increase it
                if fund_object.is_ledger_created is False:
                    bitcoin_wallet_account_object.balance += value_in_btc
                    bitcoin_wallet_account_object.save()
                    
                    particulars = 'wallet funded for {}'.format(user)
                    BitcoinNetworkLedger.objects.create(receiving_address=address,receiver_user=user,
                        amount=value_in_btc,notes="FUND WALLET",particulars=particulars,
                        reference_number = fund_object.reference_number)

                    fund_object.is_ledger_created = True
                    fund_object.save()
                    logger.info("ledger is created")

                wallet = RippleWallet.objects.get(user=user)
                is_funded = wallet.is_funded
                is_trust_line_set = wallet.is_trust_line_set
                logger.info("is_funded is",is_funded)
                customer_ripple_address = wallet.account_id

                if is_trust_line_set:#Means funded also

                    bitcoin_amount = calculate_bitcoin_amount_to_sent(value_in_btc,fund_object)        
                    logger.info("final_bitcoin amount to transfer is",bitcoin_amount)
                    response_dict = issue_btc_to_stb_wallet(customer_ripple_address,bitcoin_amount,fund_object)
                    if response_dict['error'] is True:                
                        fund_object.is_error_occurred = True
                        fund_object.status = 'failed'
                        # fund_object.transaction_verfied = True #ADITYA
                        fund_object.error_message = str(e)
                        fund_object.save()
                        return HttpResponse('*ok*')
                    logger.info("response_dict after issue_btc_to_stb_wallet @161  is",response_dict)
                    fund_object.status = "successful"

                else:#IF trust line npt set

                    if wallet.is_funded is False:
                        twenty_xrp_worth_btc = get_btc_from_xrp(20)

                        logger.info("twenty_xrp_worth_btc is ",twenty_xrp_worth_btc)

                        if settings.TEST_ENV:
                            bitcoin_wallet_account_object.balance = value_in_btc
                            bitcoin_wallet_account_object.save()


                        wallet_balance = bitcoin_wallet_account_object.balance
                        logger.info("wallet_balance is",wallet_balance)
                        if wallet_balance <  twenty_xrp_worth_btc:
                            logger.info("@173")
                            fund_object.transaction_verfied = True
                            fund_object.save()
                            message = "You have received {} BTC to activate your wallet".format(value_in_btc)
                            send_notification(user,message)
                            return HttpResponse('*ok*')

                        remaining_bitcoin = wallet_balance - twenty_xrp_worth_btc
                        fund_object.activation_fee = twenty_xrp_worth_btc
                        fund_object.save()
                        logger.info("remaining_bitcoin is",remaining_bitcoin)

                        try:
                            response_dict = set_ripple_wallet_to_receive_funds(customer_ripple_address,'activation_through_funding',fund_object.id)
                        except Exception as e:
                            logger.info("error in line@188 is",e)
                            fund_object.is_error_occurred = True
                            fund_object.status = 'failed'
                            fund_object.error_message = str(e)
                            fund_object.save()
                            return HttpResponse('not ok')

                        if response_dict['error'] is True:
                            return HttpResponse('not ok')
                        bitcoin_amount = remaining_bitcoin
                    
                    else:#wallet.is_funded is True:
                        bitcoin_amount = value_in_btc
                        request_to_set_trust_lines(customer_ripple_address)

                    bitcoin_amount = calculate_bitcoin_amount_to_sent(bitcoin_amount,fund_object) 
                    logger.info("bitcoin_amount line 228 is ",bitcoin_amount)
                    obj,created =  PendingFundTransactions.objects.get_or_create(receiver=wallet,transaction_id=fund_object.id,value = bitcoin_amount )
                    # if not obj:   
                    #     obj =  PendingFundTransactions.objects.create(receiver=wallet,transaction_id=fund_object.id,value = bitcoin_amount )

                fund_object.transaction_verfied = True
                fund_object.is_error_occurred = False
                fund_object.save()
                return HttpResponse('ok')
        except Exception as e: #MUTEX
            logger.info("Exception in MUTEX",e)
        finally:
            myLock.release()




class UpdateBalances(APIView):
    permission_classes = [AllowAny]
    def get(self, request, format=None):
        result2 = update_all_ripple_accounts()
        logger.info("result is @411",result2)
        return Response({'msg':"Success"},status=status.HTTP_200_OK)


class GetRippleBalance(APIView):
    def get(self, request, format=None):
        user = request.user
        wallet_obj = RippleWallet.objects.get(user=user)
        # account_id = wallet_obj.account_id
        btc_balance = wallet_obj.bitcoin_balance

        btc_balance_in_str = (btc_balance)
        btc_balance_to_show = '{:.8f}'.format(btc_balance_in_str)
        return Response({'btc_balance':btc_balance_in_str,"btc_balance_to_show":btc_balance_to_show},status=status.HTTP_200_OK)

class SendToSTBWallet(APIView):
    """

    1.Firstly, it is checked if user is freezed or blocked(due to excessive otp attempts)
            in serailizer, then other checks also happen and error is raised
    2.creation of NORMAL and COMMISSION transaction object using create_transaction_object()
        and if receiver is not funded then addition ACTIVATION transaction object is created 
        a.read documentation of create_transaction_object() to understand breakdown 
        
    3. creation of otp verification service and saving service_sid in transaction_obj

    4. creation of TransactionOtpAttempt to store no of otps entered by a user for a tarnsaction_id

    5. output is transaction_id
    """


    def post(self, request, format=None):
        success = {}
        error = {}
        user = request.user
        serializer = SendToSTBWalletSerializer(data=request.data,context={'request': request})
        if serializer.is_valid():
            data = serializer.data
            sender = serializer.sender
            receiver = serializer.receiver
            commission_in_btc = serializer.commission_in_btc
            wallet_activation_charge_in_btc = serializer.wallet_activation_charge_in_btc
            is_funded = receiver.is_funded
            logger.info("receiver is ",receiver)
            address = receiver.account_id
            logger.info("address in @533 is ",address)
            amount = data['amount']
            bitcoin_amount = decimal.Decimal(str(amount))
            logger.info("total send amount is ",bitcoin_amount)


            transaction_obj = create_transaction_object(sender,
                receiver,bitcoin_amount,wallet_activation_charge_in_btc,commission_in_btc)

            transaction_id = transaction_obj.id
            logger.info("transaction id is",transaction_id)

            #otp generation service
            phone_number = user.user_profile.phone_number

            logger.info("phone number is",phone_number)
            country_code = user.user_profile.nation.dialing_code

            logger.info("country code is",country_code)

            phone = str(country_code)+str(phone_number)

            service = client.verify.services.create(friendly_name='STB Verify Service')

            service_sid = (service.sid)
            transaction_obj.service_sid = service_sid
            transaction_obj.save()
            logger.info("service sid is ",service_sid)
            app_hash = settings.SMS_APP_HASH
            try:
                sms = client.verify.services(service_sid).verifications.create(
                    to=phone, channel='sms',app_hash=app_hash)




                logger.info("otp sent @232")

                t_obj = TransactionOtpAttempt.objects.create(user=user,transaction_id=transaction_id)
                return Response({"success":{'message':'OTPrequest successful',
                "transaction_id":transaction_id,"service_sid":service_sid},"error":error}, status=200)
            except Exception as e:
                logger.info("sms error is",e)
                # logger.info("sms error is",sms.errors())
                return Response({"error":{'message':'OTP request failed',"transaction_id":transaction_id},"sucsess":success}, status=503)
        if serializer.errors:
            errors = serializer.errors
            logger.info("errors in stb to stb is",errors)
            if errors.get('non_field_errors',None) is not None:
                error = {"message":errors['non_field_errors'][0]}
            elif errors.get('amount',None) is not None:
                error = {"message":errors['amount'][0]}
            elif errors.get('address',None) is not None:
                error = {"message":errors['address'][0]}
        return Response({"error":error,"success":success}, status=status.HTTP_400_BAD_REQUEST)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendStbToStbOtp(APIView):
    def post(self, request, format=None):
        success = {}
        error = {}
        user = request.user
        time_left = time_left_before_allowing_transaction(user)

        if time_left != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left)
            return Response({"error":{'message':msg},"sucsess":success}, status=403)

        data = request.data
        phone_number = user.user_profile.phone_number

        transaction_id = int(data['transaction_id'])

        stb_transaction_object = STBTransaction.objects.get(id =transaction_id)
        service_sid = stb_transaction_object.service_sid

        service = client.verify.services.create(friendly_name='STB Verify Service')

        service_sid = (service.sid)
        stb_transaction_object.service_sid = service_sid
        stb_transaction_object.save()


        logger.info("phone number is",phone_number)
        country_code = user.user_profile.nation.dialing_code

        logger.info("country code is",country_code)
        phone = str(country_code)+str(phone_number)
        app_hash = settings.SMS_APP_HASH
        try:
            sms = client.verify.services(service_sid).verifications.create(
                    to=phone, channel='sms',app_hash=app_hash)


        # sms = authy_api.users.request_sms(request.user.authy_id, {'force': True,'AppHash':"wmEllla7xTa"})

            return Response({"success":{'message':'OTP request successful'},"error":error}, status=200)

        except Exception as e :
            logger.info("error in line 389 of resend stb to stb otp is",e)
            return Response({"error":{'message':'OTP request failed'},"sucsess":success}, status=503)

class VerifyStbToStbOtp(APIView):
    """
    1.Firstly, it is checked if user is freezed or blocked(due to excessive otp attempts)
            
    2. getting service_sid from transaction_object and starting otp verification service

    3. if otp entered is wrong(verification.status != "approved"), no_of_unsuccessful_attempts in 
        TransactionOtpAttempt object increased by 1, if if becomes 5 then error message is shown and 
        user is blocked for 30 minutes

    4. if otp is verified (verification.status == "approved") new_refernce_no is created and 
        added to transaction object and that refernece no is updated in AppConfiguration table,
        and then transaction is initiated in another thread




    """
    def post(self, request, format=None):
        user = request.user
        if user.is_freezed is True:
            msg = "Your account has been freezed."
            return Response({"msg":msg,'is_blocked':True}, status=403)
        

        time_left = time_left_before_allowing_transaction(user)

        if time_left != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left)
            return Response({"msg":msg,'is_blocked':True}, status=403)

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        sender = RippleWallet.objects.get(user=user)
        logger.info("user in verify stb to stb is",user)
        
        data = request.data
        otp_entered = str(data['otp'])
        transaction_id = int(data['transaction_id'])
        secret_key = str(data['passphrase'])

       
        try:
            stb_transaction_object = STBTransaction.objects.get(id =transaction_id)
        except Exception as e:
            return Response({"msg":"invalid transaction_id",'is_blocked':False},400)

        service_sid = stb_transaction_object.service_sid
        # stb_transaction_object = STBTransaction.objects.filter(sender=sender).order_by('-created_date').first()
        if stb_transaction_object.is_otp_verfied is True:
            return Response({"msg":"OTP already verified for this transaction",'is_blocked':False}, status=status.HTTP_400_BAD_REQUEST)

        otp_attempt_object = TransactionOtpAttempt.objects.get(transaction_id = transaction_id)
        phone_number = user.user_profile.phone_number
        country_code = user.user_profile.nation.dialing_code
        phone = str(country_code)+str(phone_number)

        logger.info("phone is",phone)
        try:
            verification = client.verify.services(service_sid).verification_checks.create(
            to=phone, code=otp_entered)

        except Exception as e:
            logger.info("error is ",e)
            return Response({"msg":"OTP expired",'is_blocked':False}, status=status.HTTP_400_BAD_REQUEST)
        if verification.status != "approved":
            otp_attempt_object.no_of_unsuccessful_attempts += 1
            otp_attempt_object.save()
            if otp_attempt_object.no_of_unsuccessful_attempts >=5:
                message = "Made 5 unsuccessful attemps.As a security measure,you are disallowed to make any transaction for 30 minutes"
                return Response({"msg":message,'is_blocked':True}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"msg":"Invalid OTP or OTP expired ",'is_blocked':False}, status=status.HTTP_400_BAD_REQUEST)
        otp_attempt_object.is_successful_attempt = True
        otp_attempt_object.save()
        stb_transaction_object = STBTransaction.objects.get(id =transaction_id)
        # stb_transaction_object = STBTransaction.objects.filter(sender=sender).order_by('-created_date').first()
        if stb_transaction_object.is_otp_verfied is True:
            # create a thread to send transaction mail
            thread = threading.Thread(target=send_mail_for_transaction, args=(stb_transaction_object,))
            thread.start()            
            return Response({"msg":"OTP already verified for this transaction",'is_blocked':False}, status=status.HTTP_400_BAD_REQUEST)

        update_otp_status_and_ref_no_for_stb_transaction(stb_transaction_object,ip)
        logger.info("otp status and refrenece no updated")

        thread1 = threading.Thread(target=initiate_transaction, args=(transaction_id,secret_key))
        thread1.start()

        return Response({"msg":"OTP verified and transaction submitted",'is_blocked':False}, status=200)

class GetAddress(APIView):
    def get(self, request, format=None):
        user = request.user
        wallet_obj = RippleWallet.objects.get(user=user)
        ripple_address = wallet_obj.account_id
        user_profile_obj = UserProfile.objects.get(user=user)
        payid_obj = PayId.objects.get(user_profile = user_profile_obj)
        payid = payid_obj.get_uri()
        try:
            bitcoin_account = BitcoinWalletAccount.objects.get(user=user)
            bitcoin_address = FundingAddress.objects.filter(bitcoin_account=bitcoin_account).first().address
        except:
            bitcoin_address = None
        # bitcoin_account = BitcoinWalletAccount.objects.get(user=user)
        # bitcoin_address = FundingAddress.objects.filter(bitcoin_account=bitcoin_account).first().address
        return Response({'bitcoin_address':bitcoin_address,"payid":payid,"ripple_address":ripple_address},status=status.HTTP_200_OK)

class BasicPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = 3

class GetUserTransactions(APIView,PaginationHandlerMixin):
    pagination_class = BasicPagination

    def get(self, request, format=None):
        user = request.user
        wallet_obj = RippleWallet.objects.get(user=user)
        qs1 = STBTransaction.objects.filter(sender = wallet_obj,is_otp_verfied=True,transaction_type="NORMAL")
        qs2 = STBTransaction.objects.filter(receiver = wallet_obj,is_otp_verfied=True,transaction_type="NORMAL")

        new_queryset = qs1 | qs2 
        new_queryset = new_queryset.order_by('-created_date')
        page = self.paginate_queryset(new_queryset)
        to_send = []
        for obj in page:

            if obj.sender.user==request.user:
                transaction_type = "sent"
            else:
                transaction_type = "recd"

            commission_fees = sum(obj.related_transactions.filter(transaction_type='COMMISION').values_list('value',flat=True))
            activation_fees = sum(obj.related_transactions.filter(transaction_type='ACTIVATION').values_list('value',flat=True))
            # logger.info('commission_fees is ',commission_fees)
            # logger.info('activation_fees is ',activation_fees)
            # logger.info('sum is ',activation_fees+commission_fees)
            # commision = "{:f}".format(float(commission_fees + activation_fees)
            commision = (commission_fees + activation_fees)
                
            to_add = {
                "sender":obj.sender.user.username,
                "receiver":obj.receiver.user.username,
                "value":(obj.value),
                "status":obj.status,
                "time":obj.modified_date,
                "commision":commision,
                "wallet_activation_charge":obj.wallet_activation_charge,
                "tx_hash":obj.tx_hash,
                "reference_number":obj.reference_number,
                "type":transaction_type,
                # "web_name":get_host_from_url(settings.STB_TRANSACTION_URL),
                # "web_url":settings.STB_TRANSACTION_URL.replace("TX_HASH",obj.tx_hash)
            }
            # logger.info("to_add is",to_add)
            to_send.append(to_add)
        to_send = self.get_paginated_response(to_send)

        return Response(to_send.data,status=200)

class GetFundTransactions(APIView):
    def get(self, request, format=None):
        user = request.user
        qs = FundingTransaction.objects.filter(user=user)
        to_send = []
        for obj in qs:
            to_add = {
                "value":obj.value,
                "status":obj.status,
                "time":obj.created_date,
                "confirmations":obj.confirmations,
                "tx_hash":obj.tx_hash,
                "reference_number":obj.reference_number,
                # "web_name":get_host_from_url(settings.FUND_TRANSACTION_URL),
                # "web_url":settings.FUND_TRANSACTION_URL.replace("TX_HASH",obj.tx_hash)

            }
            to_send.append(to_add)

        return Response(to_send,status=200)

class GetExchangeRate(APIView):
    def get(self, request, format=None):
        user = request.user
        currency_obj = UserProfile.objects.get(user=user).currency_obj
        return Response({"currency_code":currency_obj.code,"exchange_rate":currency_obj.get_latest_rate()},status=200)

class GetTransactionBreakup(APIView):

    """
        A breakup of stb_wallet to stb_wallet transaction.

        Firstly, it is checked if user is freezed or blocked(due to excessive otp attempts)
            in serailizer, then other checks also happen and error is raised

        if no error is raised then output is:-

        1.total_sent by sender (commission + activation_fee + total_recvd)
        2.total_received
        3.commission(calculated using get_transaction_commission_percentage() class method 
            of STBTransaction already calculated in seriailizer)
        4.wallet_activation_charge(zero if receiver is already funded) 
        5. equivalent amount of results of 1-4 in currency of user using 
            btc_to_currency = currency_obj.get_latest_rate()
    """
    def post(self,request,format=None):
        logger.info("came in GetTransactionBreakup ")
        success = {}
        error = {}
        
        serializer = GetTransactionBreakupSerializer(data=request.data,context={'request': request})
        user = request.user
        if serializer.is_valid():
            data = serializer.data
            amount_in_btc = data.get('amount_in_btc',None)
            amount_in_currency = data.get('amount_in_currency',None)


            wallet_activation_charge_in_btc = serializer.wallet_activation_charge_in_btc
            commission_in_btc = serializer.commission_in_btc
            commission_percentage = serializer.commission_percentage
            commission_in_currency = (commission_percentage * amount_in_currency)/100
            commission_in_currency = decimal.Decimal(str(commission_in_currency))

            
            total_received_in_btc = amount_in_btc
            total_received_in_currency = amount_in_currency

            user = request.user

            currency_obj = UserProfile.objects.get(user=user).currency_obj
            currency_code = currency_obj.code
            btc_to_currency = currency_obj.get_latest_rate()

            logger.info("btc_to_currency is",btc_to_currency)

            
            wallet_activation_charge_in_currency = wallet_activation_charge_in_btc * btc_to_currency


            total_sent_in_btc = amount_in_btc + wallet_activation_charge_in_btc + commission_in_btc
            total_sent_in_currency = amount_in_currency + wallet_activation_charge_in_currency + commission_in_currency
            
            is_blocked = serializer.is_blocked
            logger.info("is_blocked is",is_blocked)


            
            commission_in_currency = '{:.2f}'.format(commission_in_currency)
            total_sent_in_currency = '{:.2f}'.format(total_sent_in_currency)
            total_received_in_currency = '{:.2f}'.format(total_received_in_currency)
            wallet_activation_charge_in_currency = '{:.2f}'.format(wallet_activation_charge_in_currency)

            commission_in_btc = (commission_in_btc)
            total_sent_in_btc = (total_sent_in_btc)
            total_received_in_btc = (total_received_in_btc)
            wallet_activation_charge_in_btc = (wallet_activation_charge_in_btc)
            
            
            receiver = serializer.receiver
            is_funded = receiver.is_funded


            user_profile_obj = UserProfile.objects.get(user=user)
            is_kyc_verfied = user_profile_obj.is_kyc_verfied

            to_send = {
                "wallet_activation_charge_in_btc":wallet_activation_charge_in_btc,
                "wallet_activation_charge_in_currency":wallet_activation_charge_in_currency,
                "currency_code":currency_code,
                "is_funded":is_funded,
                "commission_in_btc":commission_in_btc,
                "commission_in_currency":commission_in_currency,
                "total_sent_in_btc":total_sent_in_btc,
                "total_sent_in_currency":total_sent_in_currency,
                "total_received_in_btc":total_received_in_btc,
                "total_received_in_currency":total_received_in_currency,
                
                 }

            logger.info("to send is",to_send)
            return Response({"success" :to_send,"error":error,'is_blocked':is_blocked,"is_kyc_verfied":is_kyc_verfied}, status=200)
        if serializer.errors:
            logger.info("seriailzer.errors is",serializer.errors)
            is_kyc_verfied = user.user_profile.is_kyc_verfied
            try:
                is_blocked = serializer.is_blocked
            except Exception as e:
                is_blocked = False
            logger.info("is blocked is",is_blocked)
            
            errors = serializer.errors
            logger.info("error is ",errors)
            if errors.get('non_field_errors',None) is not None:
                error = {"message":errors['non_field_errors'][0]}
            elif errors.get('address',None) is not None:
                error = {"message":errors['address'][0]}
            elif errors.get('amount_in_currency',None) is not None:
                error = {"message":errors['amount_in_currency'][0]}
        return Response({"error":error,"success":success,'is_blocked':is_blocked,"is_kyc_verfied":is_kyc_verfied}, status=status.HTTP_400_BAD_REQUEST)

class GetCurrency(APIView):
    permission_classes = [AllowAny]
    def get(self,request,*args,**kwargs):
        queryset = Currency.objects.all()
        serailizer = CurrencySerializer(queryset,many=True)
        return Response(serailizer.data,status=200)

class SetTrustLines(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        success = {}
        error = {}
        data = request.data

        
        secret_key = data['passphrase']
        token = data.get('token',None)
        logger.info("token in SetTrustLines api is",token)
        if token is None:
            return Response({"error":{'message':'no token"'},"sucsess":success}, status=400)
        try:
            user = User.objects.get(token=token)
        except Exception as e:
            return Response({"error":{'message':'invalid token"'},"sucsess":success}, status=400)

        wallet_obj = RippleWallet.objects.get(user=user)
        address = wallet_obj.account_id

        if wallet_obj.is_trust_line_set is True:
            return Response({"success":{'message':'ok'},"error":error}, status=200)



        logger.info("address is",address)
        
       

        try:
            response_dict = set_trust_lines(address,secret_key)
        except Exception as e:
            logger.info("error in line 577 is",e)
            msg = e.message
            return Response({"error":{'message':msg},"sucsess":success}, status=400)


        error = response_dict['error']
        engine_result_message = response_dict['engine_result_message']


        if error is True:
            return Response({"error":{'message':engine_result_message},"sucsess":success}, status=400)


        wallet_obj.is_trust_line_set = True
        wallet_obj.save()

        logger.info("trust line set complete")
        pending_transaction_list = PendingTransactions.objects.filter(receiver=wallet_obj,is_completed=False)

        logger.info("pending_transaction_list is ",pending_transaction_list)
        logger.info("pending_transaction_list count is  ",(pending_transaction_list).count())



        central_wallet = CentralWallet.objects.filter(active=True).first().wallet
        
        if settings.PRODUCTION_ENV:    
            secret_key = central_wallet.master_key
        else:
            secret_key = central_wallet.master_seed

        for pending_transaction_obj in pending_transaction_list:
            transaction_id = pending_transaction_obj.transaction_id
            transaction_object = STBTransaction.objects.get(id=transaction_id)
            bitcoin_amount = transaction_object.value
            value_in_cad = transaction_object.value_in_cad

            logger.info("bitcoin_amount @815 is",bitcoin_amount)
            transaction_type = "CTW"
            


            ctw_transaction_object = STBTransaction.objects.create(sender=central_wallet,
            receiver=wallet_obj,value = bitcoin_amount,transaction_type=transaction_type,
            related_transaction=transaction_object,value_in_cad=value_in_cad,is_otp_verfied=True)
            logger.info("ctw_transaction_object created")
            response_dict =  create_transfer(ctw_transaction_object.id,secret_key)   
            logger.info("response_dict of create_transfer in set trtust lines is ",response_dict)

            error = response_dict['error']


            if error is True:
                # initiate_refund_from_central_wallet(transaction_object)
                logger.info("initiate_refund_from_central_wallet")
            pending_transaction_obj.is_completed = True
            pending_transaction_obj.save()




        pending_funding_list = PendingFundTransactions.objects.filter(receiver=wallet_obj,is_completed=False)
        logger.info("pending_funding_list is",pending_funding_list)

        for pending_funding_obj in pending_funding_list:
            amount = pending_funding_obj.value
            logger.info("amount in line 781 is",amount)
            fund_object = FundingTransaction.objects.get(id=pending_funding_obj.transaction_id)
            
            response_dict = issue_btc_to_stb_wallet(address,amount,fund_object)
            logger.info("issue to issue_btc_to_stb_wallet is done ")
            pending_funding_obj.is_completed = True  
            pending_funding_obj.save()  

        return Response({"success":{'message':'ok'},"error":error}, status=200)

class GetSeed(APIView):
    def get(self, request, format=None):
        user = request.user
        wallet = RippleWallet.objects.get(user=user)

        is_master_seed_noted_down = wallet.is_master_seed_noted_down
        if is_master_seed_noted_down is True:
            return Response({"msg":"key is not available"},400)

        if settings.TEST_ENV:


            secret = wallet.master_seed
        else:

            secret = wallet.master_key


        return Response({"msg":secret},200)

class DeleteSeed(APIView):
    def get(self, request, format=None):
        user = request.user
        wallet = RippleWallet.objects.get(user=user)
        wallet.master_seed = None
        wallet.master_key = None
        wallet.master_seed_hex = None
        wallet.public_key = None
        wallet.public_key_hex = None

        wallet.is_master_seed_noted_down = True
        wallet.save()

        return Response({"msg":"ok"},200)

class FundStb(APIView):
    permission_classes = [AllowAny,]
    def post(self,request):
        data = request.data
        address = data['address']
        amount = decimal.Decimal(data['amount'])
        secret_key = data['secret_key']
        logger.info("address is",address)
        msg = "ok"

        try:
            response_dict = transfer_stb_to_wallet(address,amount,secret_key)
        except Exception as e:
            logger.info("error in line 577 is",e)
            msg = e.message

        if response_dict['error'] is True:
            return Response({"msg":response_dict},status=400)
        return Response({"msg":msg},status=200)

def get_transaction_urls(request):
    #Gets the user the transaction URLs for checking 
    toret = {
        "withdraw_url":settings.WITHDRAW_TRANSACTION_URL,
        "withdraw_name":get_host_from_url(settings.WITHDRAW_TRANSACTION_URL),
        "fund_url":settings.FUND_TRANSACTION_URL,
        "fund_name":get_host_from_url(settings.FUND_TRANSACTION_URL),
        "stb_url":settings.STB_TRANSACTION_URL,
        "stb_name":get_host_from_url(settings.STB_TRANSACTION_URL),
    }
    logger.info(toret)
    return JsonResponse(toret)


def set_master_key(request):
    ripple_wallet_list = RippleWallet.objects.filter(master_key=None)
    for wallet in ripple_wallet_list:
        seed = wallet.master_seed
        j = get_mnemonic_code(seed)
        # j = "dd"
        wallet.master_key = j
        wallet.save()

    return HttpResponse("updated master key")

class SendXrp(APIView):
    def post(self,request,format=None):
        data = request.data
        logger.info("dats is",data)
        user = request.user
        logger.info("user is",user)
        sender = RippleWallet.objects.get(user=user)
        receiver_address = data['address']
        secret_key = data['secret_key']
        logger.info("receiver_address uis",receiver_address)
        amount = data['amount']
        logger.info('amount is ',amount)
        sender_address = sender.account_id
        # secret_key = sender.master_seed
        
        response_dict = xrp_transfer(sender_address,receiver_address,secret_key,amount)
        logger.info("resposne id ict is",response_dict)
        return Response({"response_dict":response_dict},status=200)


class ManualXrp(APIView):
    permission_classes = [AllowAny,]
    def post(self,request,format=None):
        data = request.data
        # logger.info("dats is",data)
        # user = request.user
        # logger.info("user is",user)
        # sender = RippleWallet.objects.get(user=user)
        receiver_address = data['receiver']
        sender_address = data['sender']
        secret_key = data['secret_key']
        logger.info("receiver_address uis",receiver_address)
        amount = data['amount']
        logger.info('amount is ',amount)
        # sender_address = sender.account_id
        # secret_key = sender.master_seed
        
        response_dict = xrp_transfer(sender_address,receiver_address,secret_key,amount)
        logger.info("resposne id ict is",response_dict)
        return Response({"response_dict":response_dict},status=200)

class CheckPassphrase(APIView):
    def post(self,request,format=None):
        data = request.data
        user = request.user

        wallet = RippleWallet.objects.get(user=user)
        if wallet.is_funded is False:
            return Response({"msg":"Ok"},status=200)
        secret = data.get('secret',None)
        if secret is None:
            return Response({"msg":"No key entered"},status=400)

        sender = RippleWallet.objects.get(user=user)
        customer_address = sender.account_id
        # sequence_error1 = True
        # while (sequence_error1==True):
        #     response_dict = fund_account(customer_address)
        #     if response_dict['engine_result']!='tefPAST_SEQ':
        #         sequence_error1 = False


        try:
            response_dict = set_trust_lines(customer_address,secret,True)
        except Exception as e:
            logger.info("error in line 978 is",str(e))
            return Response({"msg":"Incorrect passphrase entered"},status=400)
        if response_dict['error'] is True:
            return Response({"msg":"Incorrect passphrase entered"},status=400)
        else:
            return Response({"msg":"Ok"},status=200)

class SetRippling(APIView):

    permission_classes = [AllowAny,]
    def get(self,request):
        
        sequence_error = True
        while (sequence_error==True):
            trust_line_response = set_rippling()
            if trust_line_response['engine_result']!='tefPAST_SEQ':
                sequence_error = False
        if trust_line_response['error'] is True:
            return Response({"msg":trust_line_response},status=400)


        return Response({"msg":"ok"},status=200)

class GetUserFromPayid(APIView):
    def post(self,request,format=None):
        success = {}
        error = {}
        serializer = GetUserFromPayidSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            
            payid = data.get("payid",None)
            username = (payid.split('$'))[0]
            user = User.objects.get(username=username)
            user_profile_obj = UserProfile.objects.get(user=user)

            ripple_address = RippleWallet.objects.get(user=user).account_id
            payid_obj = PayId.objects.get(user_profile = user_profile_obj)
            payid = payid_obj.get_uri()

            email = user.email
           
            logger.info("username is ",username)
            return Response({"success" :{'username':username,'address':ripple_address,"email":email,"payid":payid},"error":error }, status=200)
        if serializer.errors:
            errors = serializer.errors
            logger.info("error is ",errors)
            if errors.get('non_field_errors',None) is not None:
                error = {"message":errors['non_field_errors'][0]}
            elif errors.get('address',None) is not None:
                error = {"message":errors['address'][0]}
        return Response({"error":error,"success":success}, status=status.HTTP_400_BAD_REQUEST)

class DeriveAddressFromPayid(APIView):

    permission_classes = [AllowAny,]
    def post(self,request,*args,**kwargs):
        data = request.data
        payid = data.get('payid',None)

        logger.info("payid is",payid)

        if payid is None:
            return Response({"msg":"Invalid payid"},status=400)
        if '$' not in payid:
            return Response({"msg":"Invalid payid"},status=400)



        host = (payid.split('$'))[1]
        name = (payid.split('$'))[0]
        
        host_to_compare = settings.PAYID_URI_DOMAIN
        logger.info("host is",host)
        logger.info("name is",name)
        logger.info("host_to_compare is",host_to_compare)

        if host!=host_to_compare:
            return Response({"msg":"Invalid payid"},status=400)
        try:
            payid_obj = PayId.objects.get(name__iexact=name)
        except Exception as e:
            return Response({"msg":"Invalid payid"},status=401)
        user = payid_obj.user_profile.user

        stb_wallet = RippleWallet.objects.get(user=user)
        address = stb_wallet.account_id


        btc_account = BitcoinWalletAccount.objects.get(user=user)

        btc_address = FundingAddress.objects.get(bitcoin_account = btc_account ).address



        return Response({"msg":{"xrpl_address":address,"btc_address":btc_address,"username":user.username}},status=200)

class GetLatestTransaction(APIView):
    def get(self, request, format=None):
        user = request.user
        wallet_obj = RippleWallet.objects.get(user=user)
        qs1 = STBTransaction.objects.filter(sender = wallet_obj,is_otp_verfied=True,transaction_type="NORMAL")
        qs2 = STBTransaction.objects.filter(receiver = wallet_obj,is_otp_verfied=True,transaction_type="NORMAL")

        new_queryset = qs1 | qs2 
        new_queryset = new_queryset.order_by('-created_date')
        to_send = []
        
        if new_queryset is not None:
            new_queryset = new_queryset[:5]
        for obj in new_queryset:

            if obj.sender.user==request.user:
                transaction_type = "sent"
            else:
                transaction_type = "recd"

            commission_fees = sum(obj.related_transactions.filter(transaction_type='COMMISION').values_list('value',flat=True))
            activation_fees = sum(obj.related_transactions.filter(transaction_type='ACTIVATION').values_list('value',flat=True))

            commision = (commission_fees + activation_fees)
                
            to_add = {
                "sender":obj.sender.user.username,
                "receiver":obj.receiver.user.username,
                "value":(obj.value),
                "status":obj.status,
                "time":obj.modified_date,
                "commision":commision,
                "wallet_activation_charge":obj.wallet_activation_charge,
                "tx_hash":obj.tx_hash,
                "reference_number":obj.reference_number,
                "type":transaction_type,
                "transaction_type":"STB to STB",
                # "web_name":get_host_from_url(settings.STB_TRANSACTION_URL),
                # "web_url":settings.STB_TRANSACTION_URL.replace("TX_HASH",obj.tx_hash)


            }
            # logger.info("to_add is",to_add)
            to_send.append(to_add)

        qs3 = FundingTransaction.objects.filter(user=user)
        qs3 = qs3.order_by('-created_date')
        if qs3 is not None:
            qs3 = qs3[:5]       
        for obj in qs3:
            to_add = {
                "value":obj.value,
                "status":obj.status,
                "time":obj.created_date,
                "confirmations":obj.confirmations,
                "tx_hash":obj.tx_hash,
                "transaction_type":"Fund",
                "type":"recd",
                "reference_number":obj.reference_number,
                # "web_name":get_host_from_url(settings.FUND_TRANSACTION_URL),
                # "web_url":settings.FUND_TRANSACTION_URL.replace("TX_HASH",obj.tx_hash)

            }
            to_send.append(to_add)


        wallet_obj = RippleWallet.objects.get(user=user)
    
        qs4 = WithDrawalTransaction.objects.filter(sender=wallet_obj,is_otp_verfied=True,
            transaction_type="NORMAL")

        qs4 = qs4.order_by('-created_date')
        if qs4 is not None:
            qs4 = qs4[:5]    
        for obj in qs4:
            to_add = {
                "value":obj.value_in_btc,
                "sender":obj.value_in_btc,
                "receiving_address":obj.receiving_address,
                "network fees":obj.network_fees_in_btc,
                "status":obj.status,
                "time":obj.created_date,
                # "confirmations":obj.confirmations,
                "tx_hash":obj.tx_hash_btc,
                "reference_number":obj.reference_number,
                "transaction_type":"Withdrawal",
                "type":'sent',
                # "web_name":get_host_from_url(settings.WITHDRAW_TRANSACTION_URL),
                # "web_url":settings.WITHDRAW_TRANSACTION_URL.replace("TX_HASH",obj.tx_hash_btc)
            }
            to_send.append(to_add)

        final_to_send = sorted(to_send, key = lambda i: i['time'],reverse=True)
        final_to_send = final_to_send[:5]


        return Response(final_to_send,status=200)


class GetReportData(APIView):
    permission_classes = [AllowAny,]
    def get(self, request, format=None):

        res=send_transaction_report()
        logger.info('res=',res)
        return Response(res,status=200)


# from ripple_wallet.funding_transactions/ import set_trust_lines

# from ripple_wallet.funding_transactions/ import set_trust_lines

def send_notification_to_set_trustline(wallets,new_id):
    logger.info('call to send notification for trust line')
    for wallet in wallets:
        #REMOVE IS TRUST LINE SET
        wallet.is_trust_line_set = False
        wallet.save()
        try:
            #If trust lien set with new waaletr then continue
            to_send = {
            "method": "account_lines",
            "params": [
                {
                    "account": wallet.account_id
                }
            ]
            }
            response = requests.post(settings.RIPPLE_SUBMIT_SERVER, json=to_send)
            json_response = response.json()
            
            lines = json_response['result']['lines']
            already_set = False
            for line in lines:
                if line['account'] == new_id:
                    already_set= True
                    break
            if(already_set):
                wallet.is_trust_line_set = True
                wallet.save()
                continue
            request_to_set_trust_lines(wallet.account_id)
        except Exception as e:
            logger.info('error in sending notification for account id=',str(wallet.account_id),str(e))
            continue
        #SET TRUST LINE FOR COMMISION WALLET MANULLAY
    try:
        comm_wallet= CommissionWallet.objects.filter(active=True)[0]
        logger.info(comm_wallet.wallet.master_key)
        set_trust_lines(comm_wallet.wallet.account_id,comm_wallet.wallet.master_key)
    except Exception as e:
        logger.info('error in Set Trust Line',str(e))

    logger.info('notification sends to all users')
    return



@receiver(post_save, sender=CentralWallet)
def on_change(sender, instance: CentralWallet, **kwargs):
    if instance.id is None:
        pass
    else:
        logger.info('new wallet=',instance.wallet)
        # if prev_obj.wallet==instance.wallet:
        #     pass
        # else:
            # send notification to all users to set new trust line
            # logger.info('call notification for trust line')
        stb_wallets=RippleWallet.objects.all().exclude(id=instance.wallet.id)
        # logger.info('all user wallets',stb_wallets)
        # pool=Pool(processes=1)
        # pool.apply_async(send_notification_to_set_trustline,[stb_wallets])
        thread1 = threading.Thread(target=send_notification_to_set_trustline, args=(stb_wallets,instance.wallet.account_id))
        thread1.start()