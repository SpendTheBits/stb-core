from django.db import models

# Create your models here.
from django.db import models
from decimal import Decimal
from django.conf import settings


import requests
import decimal

from django.utils import timezone
from datetime import timedelta,datetime
import threading
from xrpl_wallet.models import STBTransaction,xrplWallet
from accounts.models import User

from django.core.exceptions import ValidationError

# Create your models here.
class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class WithDrawalTransaction(BaseModel):
    types = [
    ('pending', 'Pending'),
    ('failed', 'Failed'),
    ('successful','Successful'),
    ('waiting for approval','Waiting for Approval'),
    ('request denied','Request Denied'),
    ("aprroved","Approved"),
    ("aprroved and submitted to network","Approved and submitted to network"),
    ("submitted to network","Submitted to network"),
    ]

    transaction_types = [

    ('NORMAL', 'NORMAL'),

    ('WTC','WTC'),
    ]
    sender = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,
            related_name='withdraw_transaction',null=True,blank=True)
    
    receiving_address = models.CharField(max_length=100)
    tx_hash_btc = models.CharField(max_length =300,null=True,blank=True)
    value_in_btc = models.DecimalField('value in btc',default=0.00000000, max_digits=18, decimal_places=8)
    network_fees_in_btc = models.DecimalField('network fees in btc',default=0.00000000, max_digits=18, decimal_places=8)
    value_in_cad = models.DecimalField('value in cad',default=0.00000000, max_digits=38, decimal_places=8)
    ip_address = models.CharField(max_length = 300,null=True,blank=True)
    is_otp_verfied = models.BooleanField(default=False)
    status = models.CharField(max_length = 50,choices=types,default="pending")
    service_sid = models.CharField(max_length = 300,null=True,blank=True)
    error_message = models.CharField(max_length = 300,null=True,blank=True)

    confirmations = models.IntegerField(blank=True,null=True)
    related_transaction = models.ForeignKey(STBTransaction,null=True,blank=True,on_delete=models.CASCADE,
        related_name='withdrawal_transaction')
    refund_transaction = models.ForeignKey(STBTransaction,null=True,blank=True,on_delete=models.CASCADE,
        related_name='refund_withdrawal_transaction')
    reference_number = models.CharField(max_length=300,null=True,blank=True)
    is_more_than_limit = models.BooleanField(default=False)
    transaction_type = models.CharField(
        max_length=12,
        choices=transaction_types,
        default="NORMAL",
    )
    class Meta:
        verbose_name_plural = 'Withdrawal Transactions'


    def __str__(self):
        return str(self.sender) + " " + str(self.reference_number)


class WithdrawTransactionOtpAttempt(BaseModel):
    transaction_id = models.CharField(max_length=200,unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    no_of_unsuccessful_attempts = models.IntegerField(default=0)
    is_successful_attempt = models.BooleanField(default=False)

    @classmethod
    def clear_expired_attempts(cls):
        pass
        return
    class Meta:
        ordering = ('-created_date',)

class WithdrawApproval(BaseModel):
    message = models.TextField(null=True,blank=True)
    is_declined = models.NullBooleanField(null=True,blank=True)
    is_approved = models.NullBooleanField(null=True,blank=True)
    approved_or_declined_time = models.DateTimeField(null=True,blank=True)
    request_time = models.DateTimeField(null=True,blank=True)
    xrpl_wallet = models.ForeignKey(xrplWallet,
                        on_delete=models.CASCADE,related_name='withdraw_requests',null=True,blank=True)
    
    approved_or_declined_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,related_name='admin_withdraw_requests',null=True,blank=True)
    
    value_in_btc = models.DecimalField('value in btc',default=0.00000000, max_digits=18, decimal_places=8)
    value_in_cad = models.DecimalField('value in cad',default=0.00000000, max_digits=38, decimal_places=8)
    ip_address = models.CharField(max_length = 300,null=True,blank=True)
    withdraw_transaction = models.OneToOneField(WithDrawalTransaction,on_delete=models.CASCADE,null=True,blank=True)




class WithdrawLimit(BaseModel):   
    limit_in_btc = models.DecimalField('limit in btc',default=0.00000000, max_digits=18, decimal_places=8)

    active = models.BooleanField(default=True)


    def clean(self):
        if(self.active):
            if self.limit_in_btc <= 0:
                raise ValidationError("Limit in btc cannot be negative or equal to zero")
            

            if not self.pk:#CREATE
                existing_object = WithdrawLimit.objects.filter(active=True)
                if(len(existing_object) == 1 ):
                        raise ValidationError("Only one WithdrawLimit object allowed")
        
    class Meta:
        verbose_name_plural = 'Withdraw Limit'




class NetworkFees(BaseModel):
    satoshi_per_bytes_for_fund_transaction = models.IntegerField()
    transaction_size_in_bytes_for_fund_transaction = models.IntegerField()
    satoshi_per_bytes_for_withdraw_transaction = models.IntegerField()
    transaction_size_in_bytes_for_withdraw_transaction = models.IntegerField()
    active = models.BooleanField(default=True)


    def clean(self):
        if(self.active):
            if self.satoshi_per_bytes_for_fund_transaction <= 0:
                raise ValidationError(
             "Satoshi per bytes for Fund Transaction cannot be negative or equal to zero")

            if self.transaction_size_in_bytes_for_fund_transaction <= 0:
                raise ValidationError(
                "Transaction size in bytes for Fund Transaction cannot be negative or equal to zero")


            if self.satoshi_per_bytes_for_withdraw_transaction <= 0:
                raise ValidationError(
                "Satoshi per bytes for Withdraw Transaction cannot be negative or equal to zero")

            if self.transaction_size_in_bytes_for_withdraw_transaction <= 0:
                raise ValidationError(
                "Transaction size in bytes for Withdraw Transaction cannot be negative or equal to zero")


            if not self.pk:#CREATE
                existing_object = NetworkFees.objects.filter(active=True)
                if(len(existing_object) == 1 ):
                        raise ValidationError("Only one NetworkFees object allowed")
        
    class Meta:
        verbose_name_plural = 'Network Fees'    





class Ledger(BaseModel):
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    particulars = models.TextField(max_length=1000,null=True,blank=True)
    currency = models.CharField(max_length=100)
    amount = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    notes = models.CharField(max_length=1000,null=True,blank=True)
    reference_number = models.CharField(max_length=100,null=True,blank=True)

    class Meta:
        verbose_name_plural = 'XRPL Network Ledger'

class BitcoinNetworkLedger(BaseModel):
    sending_address = models.CharField(max_length=100,null=True,blank=True)
    receiving_address = models.CharField(max_length=100,null=True,blank=True)
   
    sender_user = models.ForeignKey(User,on_delete=models.SET_NULL,
        null=True,blank=True,related_name='send_btc_ledger_entry')
    receiver_user = models.ForeignKey(User,on_delete=models.SET_NULL,
        null=True,blank=True,related_name='receive_btc_ledger_entry')

    amount = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    notes = models.CharField(max_length=1000,null=True,blank=True)
    reference_number = models.CharField(max_length=100,null=True,blank=True)
    particulars = models.TextField(max_length=1000,null=True,blank=True)