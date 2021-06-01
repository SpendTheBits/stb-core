from django.shortcuts import render
from .serializers import *
from ripple_wallet.models import *
from withdraw.models import *
from django.shortcuts import render

from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import filters
# from wallet.serializers import *
from ripple_wallet.models import *
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny
from ripple_wallet.serializers import *
import decimal
import json
import requests
from ripple_wallet.sign import sign_transaction
from ripple_wallet.serialize import serialize_object
import threading

from accounts.models import UserProfile,User
from accounts.utils import  send_notification,get_host_from_url
from blockchain.wallet import Wallet
from datetime import timedelta,datetime

import time
from ripple_wallet.ripple_utils import (update_all_ripple_accounts,
get_btc_balance_for_ripple_wallet,update_ripple_account,ledger_history,get_lastledgersequence,
get_sequence_number)
from ripple_wallet.funding_transactions import (set_ripple_wallet_to_receive_funds,
get_wallet_activation_fee_in_btc,get_btc_to_currency,time_left_before_allowing_transaction,
transfer_stb_to_wallet,set_trust_lines,set_rippling)
from withdraw.withdrawal_transaction import  (create_withdraw_transaction_object,
    time_left_before_allowing_transaction_blocked_due_to_withrawal,initiate_withdraw_transaction,
    update_otp_status_and_ref_no_for_withdraw_transaction)
from authy.api import AuthyApiClient
from ripple_wallet.submit_tx import submit_transaction
from rest_framework.settings import api_settings

from twilio.rest import Client
from payid.models import *
from withdraw.utils import withdraw_btc_from_main_wallet
# Your Account Sid and Auth Token from twilio.com/console
# DANGER! This is insecure. See http://twil.io/secure
account_sid = settings.TWILIO_ACCOUNT_SID
auth_token = settings.TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)
# Create your views here.

class WithdrawBTC(APIView):
    def post(self, request, format=None):
        success = {}
        error = {}
        user = request.user
        serializer = WithdrawBTCSerializer(data=request.data,context={'request': request})
        if serializer.is_valid():
            data = serializer.data
            logger.info("data in withdraw btc is,data")
            sender = serializer.sender
            receiving_btc_address = serializer.receiving_btc_address
            is_amount_more_than_withdrawal_limit = serializer.is_amount_more_than_withdrawal_limit
            logger.info("is_amount_more_than_withdrawal_limit",is_amount_more_than_withdrawal_limit)
            network_fees_in_btc = serializer.network_fees_in_btc
            logger.info("receiving_btc_address in @533 is ",receiving_btc_address)
            amount_in_btc = data['amount_in_btc']
           
            bitcoin_amount = decimal.Decimal(str(amount_in_btc))
            
            logger.info("total send amount is @78 ",bitcoin_amount)
            

            transaction_obj = create_withdraw_transaction_object(sender,receiving_btc_address,bitcoin_amount,network_fees_in_btc)
            if is_amount_more_than_withdrawal_limit is True:
                transaction_obj.is_more_than_limit = True
                transaction_obj.save()


            transaction_id = transaction_obj.id
            logger.info("transaction id is",transaction_id)


            phone_number = user.user_profile.phone_number

            logger.info("phone number is",phone_number)
            country_code = user.user_profile.nation.dialing_code

            logger.info("country code is",country_code)

            phone = str(country_code)+str(phone_number)
            #can not change STB Verify Service
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
                t_obj = WithdrawTransactionOtpAttempt.objects.create(user=user,transaction_id=transaction_id)
                return Response({"success":{'message':'OTP request successful',
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
            elif errors.get('amount_in_btc',None) is not None:
                error = {"message":errors['amount'][0]}
            elif errors.get('receiving_btc_address',None) is not None:
                error = {"message":errors['address'][0]}
        return Response({"error":error,"success":success}, status=status.HTTP_400_BAD_REQUEST)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

