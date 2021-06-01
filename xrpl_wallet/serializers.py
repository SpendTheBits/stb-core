from rest_framework import serializers
from xrpl_wallet.models import *
import decimal
from accounts.models import UserProfile
from xrpl_wallet.funding_transactions import (get_wallet_activation_fee_in_btc,
get_wallet_activation_fee_in_currency,get_btc_to_currency,
time_left_before_allowing_transaction,check_if_less_than_10_cad)

from payid.utils import get_payid_object,derive_btc_address_from_payid
from accounts.models import UserProfile
from django.conf import settings
from payid.models import PayId
from withdraw.withdrawal_transaction import(time_left_before_allowing_transaction_blocked_due_to_withrawal,

)
class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'

class SendToSTBWalletSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=8,coerce_to_string=False)
    commission_in_btc = serializers.DecimalField(max_digits=18, decimal_places=8,coerce_to_string=False)
    payid = serializers.CharField()


    def validate(self, data):
        #checks in order

        #1. if account freezed
        #1.1 if kyc verified or not
        #2. if payid entered is valid or not
        #3. if sending to oneself
        #4. if receiver is freeze or not
        #5. amount_in_btc <= 0
        #6. if blocked due to 5 invalid otps for wallet transaction
        #7. if blocked due to 5 invalid otps for withdrawal transactions
        #8. insufficient balance

        amount = data['amount']
        payid = data['payid']
        commission_in_btc = data['commission_in_btc']

        logger.info("payid is",payid)

        request = self.context.get('request')
        user = request.user
        logger.info('user is',user) 
        user_profile_obj = UserProfile.objects.get(user=user)

        #checking 1
        if user.is_freezed is True:
            msg = "Your account has been freezed."
            self.is_blocked = True
            raise serializers.ValidationError(msg)
        

        #checking 1.1
        if user_profile_obj.is_kyc_verfied is False:
            msg = "Kyc not done"            
            raise serializers.ValidationError(msg)   


        #checking 2
        payid_obj = get_payid_object(payid)

        if payid_obj is None:
            raise serializers.ValidationError("Invalid payid")


        #checking 3    
        sender = xrplWallet.objects.get(user=user)  
        receiver_user = payid_obj.user_profile.user
        receiver = xrplWallet.objects.get(user=receiver_user)

        if receiver == sender:
            raise serializers.ValidationError("Can not send bitcoin to yourself")


        #checking 4
        if receiver_user.is_freezed is True:
            msg = "Receiver account has been freezed.No Transaction allowed"
            self.is_blocked = True
            raise serializers.ValidationError(msg)



        #checking 5
        if amount <= 0:
            raise serializers.ValidationError("Invalid amount")
        
        #checking 6   
        time_left = time_left_before_allowing_transaction(user)
        logger.info("time_left is",time_left)
        if time_left != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left)
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #checking 7    
        time_left_due_to_withdrawal = time_left_before_allowing_transaction_blocked_due_to_withrawal(user)
        logger.info("time_left_due_to_withdrawal is",time_left_due_to_withdrawal)

        if time_left_due_to_withdrawal != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left_due_to_withdrawal)
            self.is_blocked = True
            raise serializers.ValidationError(msg)


      
        balance_in_btc = sender.bitcoin_balance 

        if receiver.is_funded is False:
            wallet_activation_charge_in_btc = get_wallet_activation_fee_in_btc()
        else:
            wallet_activation_charge_in_btc = decimal.Decimal(0)

        
        logger.info("balance_in_btc is",balance_in_btc)


        amount_to_charge_in_btc = commission_in_btc + wallet_activation_charge_in_btc + amount
        logger.info("amount_to_charge_in_btc in serializer is",amount_to_charge_in_btc)
        #checking 8
        if balance_in_btc - amount_to_charge_in_btc < 0:
            raise serializers.ValidationError("Insufficient balance")


        self.sender = sender
        self.receiver = receiver
        
        self.wallet_activation_charge_in_btc = wallet_activation_charge_in_btc
        self.commission_in_btc = commission_in_btc
        return data





class GetUserFromPayidSerializer(serializers.Serializer):
    payid = serializers.CharField()
    def validate(self, data):
        payid = data['payid']

        result = get_payid_object(payid)

        if result is None:
            raise serializers.ValidationError("Invalid payid")

        return data





class GetTransactionBreakupSerializer(serializers.Serializer):
    amount_in_btc = serializers.DecimalField(max_digits=18, decimal_places=8,coerce_to_string=False)
    amount_in_currency = serializers.DecimalField(max_digits=18, decimal_places=2,coerce_to_string=False)
    payid = serializers.CharField()

    def validate(self, data):

        #checks in order


        #1. if account freezed
        #1.1 if kyc verified or not
        #2. if payid entered is valid or not
        #3. if sending to oneself
        #4. if receiver is freeze or not
        #5. amount_in_btc <= 0
        #6. if blocked due to 5 invalid otps for wallet transaction
        #7. if blocked due to 5 invalid otps for withdrawal transactions
        #8. insufficient balance
        
        amount_in_btc = data['amount_in_btc']
        amount_in_currency = data['amount_in_currency']
        logger.info("amount_in_btc is",amount_in_btc)
        logger.info("amount_in_currency is",amount_in_currency)

        payid = data['payid']
        logger.info("payid is",payid)

        request = self.context.get('request')
        user = request.user
        user_profile_obj = UserProfile.objects.get(user=user)
        currency_code = user_profile_obj.currency_obj.code
        
        logger.info('user in serializer is',user)        
        logger.info('currency_code is',currency_code)        

        #checking 1
        if user.is_freezed is True:
            msg = "Your account has been freezed.No Transaction allowed"
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #checking 1.1
        if user_profile_obj.is_kyc_verfied is False:
            msg = "Kyc not done"            
            raise serializers.ValidationError(msg)            
        
        #checking 2
        payid_obj = get_payid_object(payid)

        if payid_obj is None:
            raise serializers.ValidationError("Invalid payid")

        receiver_user = payid_obj.user_profile.user

        #checking 3
        sender = xrplWallet.objects.get(user=user)  
        
        receiver = xrplWallet.objects.get(user=receiver_user)

        if receiver == sender:
            raise serializers.ValidationError("Can not send bitcoin to yourself")




        #checking 4
        if receiver_user.is_freezed is True:
            msg = "Receiver account has been freezed.No Transaction allowed"
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #checking 5
        if amount_in_btc <= 0:
            raise serializers.ValidationError("Invalid amount")



        #checking 6    
        time_left = time_left_before_allowing_transaction(user)
        logger.info("time_left is",time_left)
        if time_left != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left)
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        #checking 7
        time_left_due_to_withdrawal = time_left_before_allowing_transaction_blocked_due_to_withrawal(user)
        logger.info("time_left_due_to_withdrawal is",time_left_due_to_withdrawal)

        if time_left_due_to_withdrawal != 0:
            msg = "Disallowed to do transaction for another {} minutes".format(time_left_due_to_withdrawal)
            self.is_blocked = True
            raise serializers.ValidationError(msg)

        
        #checking 8
                
        balance_in_btc = sender.bitcoin_balance 
        commission_percentage = STBTransaction.get_transaction_commission_percentage(amount_in_currency,
            currency_code)
        logger.info("commission_percentage is",commission_percentage)
        commission_in_btc =(amount_in_btc * commission_percentage)/100
        logger.info("commission_in_btc is",commission_in_btc)

        if receiver.is_funded is False:
            wallet_activation_charge_in_btc = get_wallet_activation_fee_in_btc()
        else:
            wallet_activation_charge_in_btc = decimal.Decimal(0)

        
        logger.info("balance_in_btc is",balance_in_btc)


        amount_to_charge_in_btc = commission_in_btc + wallet_activation_charge_in_btc + amount_in_btc
        logger.info("amount_to_charge_in_btc in serializer is",amount_to_charge_in_btc)

        if balance_in_btc - amount_to_charge_in_btc < 0:
            raise serializers.ValidationError("Insufficient balance")

        self.wallet_activation_charge_in_btc = wallet_activation_charge_in_btc
        self.commission_in_btc = commission_in_btc
        self.commission_percentage = commission_percentage
        self.is_blocked = False
        self.receiver = receiver


        logger.info("serailizer checking is done")
        return data



