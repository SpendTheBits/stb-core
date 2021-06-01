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
from django.core.exceptions import ValidationError

# Create your models here.


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Currency(BaseModel):
    name = models.CharField(max_length=300,null=True,blank=True)
    code = models.CharField(max_length=30,unique=True)
    class Meta:
        verbose_name_plural = 'Currencies'
        ordering = ('code',)

    def get_latest_rate(self):
        logger.info("came in get_latest_rate ")
        latest_rate = ExchangeRate.objects.filter(currency=self).last()#latest('created_date')
        validity_in_min = AppConfiguration.objects.filter(active=True).first().exchange_rate_validity
        if(timezone.now()-latest_rate.created_date) < timedelta(minutes = validity_in_min):
            return latest_rate.rate
        else:
            rate = self.fetch_exchange_rate()
            return rate
        return None

    def fetch_exchange_rate(self):
        logger.info("came in fetch_exchange_rate")
        request_url = "https://api.coinbase.com/v2/prices/spot?currency="+str(self.code)
        response = requests.get(request_url)
        json_response = response.json()
        btc_to_currency = json_response['data']['amount']
        btc_to_currency = decimal.Decimal(btc_to_currency)
        ex_rate = ExchangeRate()
        ex_rate.rate=btc_to_currency
        ex_rate.currency=self
        ex_rate.save()
        return btc_to_currency
        

    @classmethod
    def get_equivalent_amount_in_cad(cls,amount_in_currency,currency_code):
        currency = Currency.objects.get(code__iexact="CAD")
        if currency_code=="CAD":
            return amount_in_currency
        if currency_code == "BTC":
            logger.info("came here becauase cached in db 311")
            amount_in_cad = currency.get_latest_rate() * decimal.Decimal(amount_in_currency)
            return amount_in_cad

    def __str__(self):
        return str(self.code)

#TODO
class ExchangeRate(BaseModel):
    currency = models.ForeignKey(Currency,on_delete=models.CASCADE)
    rate=models.DecimalField(verbose_name='exchange rate',default=0.00000000, max_digits=38, decimal_places=12)
    date_time=models.DateTimeField(default=datetime.now)



def get_btc_to_currency(currency_code):
    request_url = env('coinbase_url')+str(currency_code)
    response = requests.get(request_url)
    json_response = response.json()
    btc_to_currency = json_response['data']['amount']
    btc_to_currency = decimal.Decimal(btc_to_currency)
    return btc_to_currency


class AdminEmail(BaseModel):
    email = models.EmailField(unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.email

class xrplWallet(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='xrpl_wallet')
    account_id = models.CharField('xrpl address',max_length = 100)
    key_type = models.CharField(max_length = 100,null=True,blank=True)
    public_key = models.CharField(max_length = 100,null=True,blank=True)
    public_key_hex = models.CharField(max_length = 100,null=True,blank=True)
    is_funded = models.BooleanField(default=False)
    is_trust_line_set = models.BooleanField(default=False) #Trust Line Set with us
    is_master_seed_noted_down = models.BooleanField(default=False) # Customer noted down master seed
    xrpl_balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    bitcoin_balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)


    def __str__(self):
        return str(self.user)
    class Meta:
        verbose_name_plural = 'STB Wallet'


class BitcoinWalletAccount(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='bitcoin_account')
    xpub = models.CharField(max_length=400,null=True,blank=True)
    balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    index = models.IntegerField(null=True,blank=True)
    class Meta:
        verbose_name_plural = 'Bitcoin Wallet'

    def __str__(self):
        return str(self.user)


class FundingAddress(BaseModel):
    address = models.CharField(max_length=100, unique=True)
    bitcoin_account = models.OneToOneField(BitcoinWalletAccount,on_delete=models.CASCADE,related_name='receiving_address')
    receiveIndex = models.IntegerField(null=True,blank=True)
    class Meta:
        ordering = ['-created_date']
    def __str__(self):
        return str(self.bitcoin_account.user)+" "+str(self.receiveIndex)


class AppConfiguration(BaseModel):
    # TODO : Add ACTIVE to list VIEW ( REd color for inactive)
    name = models.CharField(max_length=40)
    active = models.BooleanField(default=True)
    # issuer_wallet = models.OneToOneField(xrplWallet,on_delete = models.CASCADE,null=True)
    minimum_xrpl_balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    minimum_bitcoin_balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    confirmation_amount_in_btc = models.DecimalField('Max amount in BTC for 1 confirmation',default=0.00000000, 
        max_digits=18, decimal_places=8)
    current_reference_number = models.CharField("STB to STB Transaction Reference Number",
            max_length=300,null=True,blank=True)
    current_withdraw_reference_number = models.CharField("Withdraw Transaction Reference Number",
        max_length=300,null=True,blank=True)
    current_fund_transaction_reference_number = models.CharField("Fund Transaction Reference Number",
            max_length=300,null=True,blank=True)
    exchange_rate_validity = models.PositiveIntegerField(help_text="In minutes",default=5)
    coindesk_api_key = models.CharField(max_length=40,default='1f6923b0f855490a83dc1a2e8baeab26')
    cold_wallet_address = models.CharField(max_length=100, null=True,blank=True)
    # is_updation_started = models.BooleanField(default=False)
    email=models.CharField(max_length=30,null=True,blank=True)
    
    def clean(self, *args, **kwargs):
        if self.minimum_xrpl_balance <= 0:
            raise ValidationError("minimum xrpl balance cannot be negative or equal to zero")

        if self.minimum_bitcoin_balance <= 0:
            raise ValidationError("minimum bitcoin balance cannot be negative or equal to zero")

        if(self.active):
            if not self.pk:#CREATE
                logger.info("@90")
                existing_configurations = AppConfiguration.objects.filter(active=True)
                if(len(existing_configurations) == 1 ):
                        raise ValidationError("Only one conf file allowed")
        

    def __str__(self):
        return str(self.name)
    class Meta:
        verbose_name_plural = 'AppConfiguration'

class Commission(BaseModel):
    PERCENT='PERCENT'
    FIXED='FIXED'
    #TODO : Add Active Column to List View
    name=models.CharField(max_length=50,null=True,blank=True)
    active = models.BooleanField(default=True)
    types = [
    ('PERCENT', 'PERCENT'),
    ('FIXED', 'FIXED'),
    ]
    fund_wallet_comm_type=models.CharField(
        max_length=7,
        choices=types,
        default=PERCENT,
    )
    transaction_comm_type=models.CharField(
        max_length=7,
        choices=types,
        default=PERCENT,
    )
    fund_wallet_commision = models.DecimalField(max_digits=18,decimal_places=10,verbose_name=u"Percentage Commission for Fund Transactions")
    transaction_commision = models.DecimalField(max_digits=18,decimal_places=10,verbose_name=u"Percentage Commission for Wallet Transactions")
    min_transaction_amt= models.DecimalField(max_digits=18,decimal_places=10,verbose_name=u"Min amount for which this configuration applies.(Non Inclusive)")
    max_transaction_amt= models.DecimalField(max_digits=18,decimal_places=10,verbose_name=u"Max amount for which this configuration applies(Inclusive).")
    def save(self, *args, **kwargs):
        #TODO : If DEBUG FALSE, Hanfle how erroer is displayed
        if(self.active):
            if self.fund_wallet_commision <=0:
                raise ValueError("fund wallet commission can not be zero or less")

            if self.transaction_comm_type=="PERCENT" and  self.fund_wallet_commision >=100:
                raise ValueError("fund wallet commission percentage can not be 100 or more")
            if self.transaction_commision <=0:
                raise ValueError("STB transaction commission can not be zero or less")
            existing_configurations = Commission.objects.filter(active=True)
            for conf in existing_configurations:
                if conf == self:
                    continue
                overlap = self.min_transaction_amt < conf.max_transaction_amt and conf.min_transaction_amt < self.max_transaction_amt
                if(overlap):
                    raise ValueError("Range clashes with "+conf.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

class FundingTransaction(BaseModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,related_name='receive_transaction',null=True,blank=True)
    tx_hash = models.CharField(max_length =300,unique = True)
    transaction_verfied = models.BooleanField(default=False)
    is_ledger_created = models.BooleanField(default=False)
    value = models.DecimalField('sent',default=0.00000000, max_digits=18, decimal_places=8)
    value_in_cad = models.DecimalField('value in cad',default=0.00000000, max_digits=38, decimal_places=8)
    commission = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    received = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    activation_fee = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    is_error_occurred = models.BooleanField(default = False)
    error_message = models.CharField(max_length = 500,null=True,blank=True)
    error_code = models.CharField(max_length = 50,null=True,blank=True)
    error_tx_hash = models.CharField(max_length =300,null=True,blank=True)
    status = models.CharField(max_length = 30,default="pending")
    confirmations = models.IntegerField(blank=True,null=True)
    reference_number = models.CharField(max_length=300,null=True,blank=True)
    class Meta:
        verbose_name_plural = 'Fund Transactions'
    def __str__(self):
        return str(self.user)


class CentralWallet(BaseModel):
    wallet = models.OneToOneField(xrplWallet,on_delete = models.CASCADE,null=True)
    active = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        if(self.active):
            if not self.pk:#CREATE
                existing_object = CentralWallet.objects.filter(active=True)
                if(len(existing_object) >1 ):
                        raise ValueError("Only one Issuer Wallet object allowed")
        super().save(*args, **kwargs)



    class Meta:
        verbose_name_plural = 'Central Wallet'


class STBTransaction(BaseModel):
    types = [
    ('COMMISION', 'COMMISION'),
    ('NORMAL', 'NORMAL'),
    ('FUNDWALLET','FUNDWALLET'),
    ('WTC','WTC'),
    ('CTW','CTW'),
    ('REFUND WITHDRAWAL','REFUND WITHDRAWAL'),
    ('WITHDRAWAL','WITHDRAWAL'),
    ('ACTIVATION','ACTIVATION'),
    ('REFUND COMMISION','REFUND COMMISION'),
    ('REFUND ACTIVATION','REFUND ACTIVATION'),
    
    ] #ADD DESCRIPTION OF WTC etc
    value = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    value_in_cad = models.DecimalField(default=0.00000000, max_digits=38, decimal_places=8)
    sender = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='stb_sender_transaction')
    receiver = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='stb_receiver_transaction')
    wallet_activation_charge = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    is_otp_verfied = models.BooleanField(default=False)
    is_validated = models.BooleanField(default=False)
    status = models.CharField(max_length = 30,default="pending")
    tx_hash = models.CharField(max_length=200,null=True,blank=True)
    last_ledger_sequence = models.CharField(max_length =30,null=True,blank=True)
    sequence = models.CharField(max_length =10,null=True,blank=True)
    error_message = models.CharField(max_length = 500,null=True,blank=True)
    error_code = models.CharField(max_length = 50,null=True,blank=True)
    related_transaction = models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE,related_name='related_transactions')
    related_funding_transaction = models.ForeignKey(FundingTransaction,
        null=True,blank=True,on_delete=models.CASCADE,related_name='stb_wallet_transaction')
    reference_number = models.CharField(max_length=300,null=True,blank=True)
    service_sid = models.CharField(max_length = 300,null=True,blank=True)
    ip_address = models.CharField(max_length = 300,null=True,blank=True)
    notes = models.TextField(null=True,blank=True)
    transaction_type = models.CharField(
        max_length=50,
        choices=types,
        default="NORMAL",
    )


    class Meta:
        verbose_name_plural = 'Wallet Transactions'
    
    def __str__(self):
        return str(self.value)
    @classmethod
    def get_transaction_commission(cls,amount_to_calculate):
        logger.info("amount to calculate is",amount_to_calculate)
        amount_to_calculate = Decimal(amount_to_calculate)
        
        amount_in_cad = Currency.get_equivalent_amount_in_cad(amount_to_calculate,"BTC")
        # else:
        #     amount_in_cad = amount_to_calculate

        # amount = get_btc_to_currency("CAD") * Decimal(amount_to_calculate)
        # logger.info("amount is ",amount)
        #Returns commision for a transaction in BTC
        existing_configurations = Commission.objects.filter(active=True)
        for conf in existing_configurations:
            overlap = conf.min_transaction_amt < amount_in_cad and conf.max_transaction_amt >= amount_in_cad
            if(overlap):
                if(conf.transaction_comm_type==conf.PERCENT):
                    commission_in_cad = amount_in_cad*conf.transaction_commision/Decimal(100)
                  
                    commission_in_currency = commission_in_cad / Decimal(Currency.get_equivalent_amount_in_cad(1,"BTC"))

                    logger.info("commission_in_currency is",commission_in_currency)
                    return commission_in_currency



                    # commission = amount*conf.transaction_commision/Decimal(100)
                    # commission = commission / Decimal(get_btc_to_currency("CAD"))
                    # return commission
                else:
                    return conf.transaction_commision
        # return (amount_to_calculate*Decimal(0.01))
        return Decimal(amount_to_calculate)*Decimal(0.01)
        # return 0


    @classmethod
    def get_fundwallet_commission(cls,amount_to_calculate):
        amount = get_btc_to_currency("CAD") * Decimal(amount_to_calculate)
        #Returns commision for a transaction in BTC
        existing_configurations = Commission.objects.filter(active=True)
        for conf in existing_configurations:
            overlap = conf.min_transaction_amt < amount and conf.max_transaction_amt >= amount
            if(overlap):
                if(conf.transaction_comm_type==conf.PERCENT):
                    commission= amount*conf.fund_wallet_commision/Decimal(100)
                    commission = commission / Decimal(get_btc_to_currency("CAD"))
                    return commission
                else:
                    return conf.fund_wallet_commision
                   
        return (amount_to_calculate*Decimal(0.01))
        # return 0

    @classmethod
    def get_transaction_commission_percentage(cls,amount_in_currency,currency_code):
        logger.info("amount_in_currency is",amount_in_currency)
        logger.info("currency_code is",currency_code)
        amount_in_currency = Decimal(amount_in_currency)
        
        if currency_code=="CAD":
            amount_in_cad = amount_in_currency
        else:
            amount_in_cad = Currency.get_equivalent_amount_in_cad(amount_in_currency,currency_code)
        existing_configurations = Commission.objects.filter(active=True)
        for conf in existing_configurations:
            overlap = conf.min_transaction_amt < amount_in_cad and conf.max_transaction_amt >= amount_in_cad
            if(overlap):
                return conf.transaction_commision    
        return 1





class TransactionOtpAttempt(BaseModel):
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


class Minimumbalance(BaseModel):
    minimum_xrpl_balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    minimum_bitcoin_balance = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)
    send_email_to = models.EmailField()
    active = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        if(self.active):
            if not self.pk:#CREATE
                existing_object = Minimumbalance.objects.filter(active=True)
                if(len(existing_object) >1 ):
                        raise ValueError("Only one minimum balance object allowed")
        super().save(*args, **kwargs)





class AppNotification(BaseModel):
    message = models.TextField()
    is_published = models.BooleanField(default=False)
    sent_time = models.DateTimeField(null=True,blank=True)



class PendingTransactions(BaseModel):
    receiver = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='pending_transaction')
    is_completed = models.BooleanField(default=False)
    transaction_id = models.IntegerField(null=True,blank=True)    
    tx_blob = models.CharField(max_length=1000,null=True,blank=True)
    sender = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='sender_pending_transaction',null=True,blank=True)
    sender_secret_key = models.CharField(max_length=100,null=True,blank=True)
    sequence_number = models.IntegerField(null=True,blank=True)

    class Meta:
        verbose_name_plural = 'Pending Wallet Transactions'


class PendingTrustLines(BaseModel):
    receiver = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='pending_trustlines')
    device_key = models.CharField(max_length=1200)
    is_completed = models.BooleanField(default=False)



class PendingFundTransactions(BaseModel):
    receiver = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='pending_funding_transaction')
    is_completed = models.BooleanField(default=False)
    transaction_id = models.IntegerField(null=True,blank=True,unique=True)
    value = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)

    class Meta:
        verbose_name_plural = 'Pending Fund Transactions'


class CommissionWallet(BaseModel):
    wallet = models.OneToOneField(xrplWallet,on_delete = models.CASCADE,null=True)
    active = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        if(self.active):
            if not self.pk:#CREATE
                existing_object = CommissionWallet.objects.filter(active=True)
                if(len(existing_object) >1 ):
                        raise ValueError("Only one Issuer Wallet object allowed")
        super().save(*args, **kwargs)



    class Meta:
        verbose_name_plural = 'Commission Wallet'






class XrpTransaction(BaseModel):
    types = [
    ('activation_through_funding', 'activation_through_funding'),
    ('activation_through_wallet', 'activation_through_wallet'),

    
    ] 
    value_in_xrp = models.DecimalField(default=0.00000000, max_digits=18, decimal_places=8)

    sender = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='xrp_sender_transaction',
                    null=True,blank=True)
    receiver = models.ForeignKey(xrplWallet,on_delete = models.CASCADE,related_name='xrp_receiver_transaction',
                    null=True,blank=True)

    is_validated = models.BooleanField(default=False)
    status = models.CharField(max_length = 30,default="pending")
    tx_hash = models.CharField(max_length=200,null=True,blank=True)
    last_ledger_sequence = models.CharField(max_length =30,null=True,blank=True)
    sequence = models.CharField(max_length =10,null=True,blank=True)
    error_message = models.CharField(max_length = 500,null=True,blank=True)
    error_code = models.CharField(max_length = 50,null=True,blank=True)
    related_transaction_id = models.PositiveIntegerField(null=True,blank=True)

    transaction_type = models.CharField(
        max_length=50,
        choices=types,
        null=True,blank=True
    )