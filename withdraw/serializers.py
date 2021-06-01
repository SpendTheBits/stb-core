from rest_framework import serializers
from ripple_wallet.models import *

import decimal
from accounts.models import UserProfile
from ripple_wallet.funding_transactions import (get_wallet_activation_fee_in_btc,
get_wallet_activation_fee_in_currency,get_btc_to_currency,
time_left_before_allowing_transaction,check_if_less_than_10_cad)

from payid.utils import get_payid_object,derive_btc_address_from_payid
from accounts.models import UserProfile
from django.conf import settings
from payid.models import PayId
from withdraw.withdrawal_transaction import(time_left_before_allowing_transaction_blocked_due_to_withrawal,)
from withdraw.utils import (calculate_network_fees,check_if_more_than_withdrawal_limit,
check_if_amount_more_than_spendable_balance)

from ripple_wallet import bitgo_utils
class WithdrawBTCSerializer(serializers.Serializer):
    amount_in_btc = serializers.DecimalField(max_digits=18, decimal_places=8,coerce_to_string=False)
    receiving_btc_address = serializers.CharField(required=False)


    def validate(self, data):
        #0 .if account freezed
        #1 .receiving_btc_address is valid or not
        #2. if blocked due to 5 invalid otps for wallet transaction
        #3. if blocked due to 5 invalid otps for withdrawal transactions
        #4. if sending to oneself
        #5. amount_in_btc <= 0
        #6. insufficient balance
        #7. is more than_central wallet balance 

        self.is_amount_more_than_withdrawal_limit = False
        amount_in_btc = data['amount_in_btc']
    
        receiving_btc_address = data.get("receiving_btc_address",None)

        logger.info("amount_in_btc is",amount_in_btc)
        logger.info("receiving_btc_address is",receiving_btc_address)




        request = self.context.get('request')
        user = request.user
        sender = RippleWallet.objects.get(user=user)          
        balance_in_btc = sender.bitcoin_balance  
      
        #check 0
        if user.is_freezed is True:
            msg = "Your account has been freezed."
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #check 1 : ADDRESS VALID
        try:
            if not bitgo_utils.verify_btc_address(receiving_btc_address):
                raise serializers.ValidationError("Invalid address")
        except Exception as e:
            logger.info("error is in Verify BTC ADDRESS ",e)
            raise serializers.ValidationError("Error in verifying address")


        sender_bitcoin_address = BitcoinWalletAccount.objects.get(user=user).receiving_address.address

        time_left = time_left_before_allowing_transaction(user)
        time_left_due_to_withdrawal = time_left_before_allowing_transaction_blocked_due_to_withrawal(user)
        #check 2
        if time_left != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left)
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #check 3
        if time_left_due_to_withdrawal != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left_due_to_withdrawal)
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #check 4
        if sender_bitcoin_address == receiving_btc_address:
             raise serializers.ValidationError("Can not send bitcoin to yourself")
            
        #check 5
        if amount_in_btc <= 0 :
            raise serializers.ValidationError("Invalid amount ")

        #check 6 
        amount_in_btc = decimal.Decimal(amount_in_btc)

        logger.info('amount in btc is',amount_in_btc)
        network_fees_in_btc = calculate_network_fees()
        logger.info("network_fees_in_btc is@93",network_fees_in_btc)
        if balance_in_btc - (amount_in_btc +network_fees_in_btc) < 0:
            raise serializers.ValidationError("Insufficient balance")

        is_amount_more_than_withdrawal_limit = check_if_more_than_withdrawal_limit(amount_in_btc)
        self.sender = sender
        # self.is_amount_more_than_withdrawal_limit = is_amount_more_than_withdrawal_limit
        self.is_amount_more_than_withdrawal_limit = is_amount_more_than_withdrawal_limit
       
        self.receiving_btc_address = receiving_btc_address
        self.network_fees_in_btc = network_fees_in_btc
        logger.info("serailizer ended of withdraw btc")
        return data


class GetWithdrawTransactionBreakupSerializer(serializers.Serializer):
    amount_in_btc = serializers.DecimalField(max_digits=18, decimal_places=8,coerce_to_string=False)
    amount_in_currency = serializers.DecimalField(max_digits=18, decimal_places=2,coerce_to_string=False)
    receiving_btc_address = serializers.CharField()
    
    

    def validate(self, data):

        #checks
        #0 .if account freezed
        #0.1 kyc done or not
        #1 .receiving_btc_address is valid or not

        #4. if sending to oneself
        #5. amount_in_btc <= 0
        #6. insufficient balance
        #7. is more than_central wallet balance 
        self.is_blocked = False
        self.is_withdrawal_limit_crossed = False
        amount_in_btc = data['amount_in_btc']
        request = self.context.get('request')
        user = request.user

        user_profile_obj = UserProfile.objects.get(user=user)

        logger.info("amount_in_btc in ",amount_in_btc)

        # payid = data.get('payid',None)
        receiving_btc_address = data.get("receiving_btc_address",None)
        
        logger.info("receiving_btc_address in ",receiving_btc_address)

        #check 0
        if user.is_freezed is True:
            msg = "Your account has been freezed."
            self.is_blocked = True
            raise serializers.ValidationError(msg)


        #checking 0.1
        if user_profile_obj.is_kyc_verfied is False:
            msg = "KYC not done"            
            raise serializers.ValidationError(msg)       


        #check 1 : ADDRESS VALID
        try:
            if not bitgo_utils.verify_btc_address(receiving_btc_address):
                raise serializers.ValidationError("Invalid address")
        except Exception as e:
            logger.info("error is in Verify BTC ADDRESS ",e)
            raise serializers.ValidationError("Error in verifying address")

        time_left = time_left_before_allowing_transaction(user)
        time_left_due_to_withdrawal = time_left_before_allowing_transaction_blocked_due_to_withrawal(user)
        logger.info("time_left in withdarwal breakup sertiailizer",time_left_due_to_withdrawal)
        logger.info("time_left in stb breakup sertiailizer",time_left)
        sender = RippleWallet.objects.get(user=user)          
        balance_in_btc = sender.bitcoin_balance 

        sender_bitcoin_address = BitcoinWalletAccount.objects.get(user=user).receiving_address.address
        


        #check 4
        if sender_bitcoin_address == receiving_btc_address:
            raise serializers.ValidationError("Can not send bitcoin to yourself")

        #check 5
        if amount_in_btc <= 0:
            raise serializers.ValidationError("Invalid amount")

        #check 6
        network_fees_in_btc= calculate_network_fees()
        
        if balance_in_btc - (amount_in_btc +network_fees_in_btc) < 0:
            raise serializers.ValidationError("Insufficient balance")


        #check 7
        is_more_than_cw_balance = check_if_amount_more_than_spendable_balance(amount_in_btc)
        logger.info('is_more_than_cw_balance is',is_more_than_cw_balance)
        if is_more_than_cw_balance:
            raise serializers.ValidationError(
        "Some issues are occuring processing large amount, please try after some time or try with less amount")

        is_amount_more_than_withdrawal_limit = check_if_more_than_withdrawal_limit(amount_in_btc)
        logger.info('is_amount_more_than_withdrawal_limit is',is_amount_more_than_withdrawal_limit)
        
        if is_amount_more_than_withdrawal_limit:
            self.is_withdrawal_limit_crossed = True
        
        logger.info("balance_in_btc is",balance_in_btc)

        self.receiving_btc_address = receiving_btc_address
        self.network_fees_in_btc = network_fees_in_btc
        

        logger.info("serailizer checking is done")
        return data