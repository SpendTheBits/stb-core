from django.contrib import admin
from .models import *

from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from django.conf.urls import url
from django.urls import reverse
from django.http import HttpResponseRedirect
from push_notifications.models import APNSDevice, GCMDevice
from django.utils.timezone import now
from django.utils.html import format_html
from xrpl_wallet.xrpl_utils import update_all_xrpl_accounts,update_xrpl_account
from django.conf import settings
from .funding_transactions import *
from withdraw.models import *
from fcm_django.models import FCMDevice
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ExportActionModelAdmin,ExportMixin
from import_export import fields, resources

def get_payid_uri( name ):
    return ''.join((name.lower(), '$', settings.PAYID_URI_DOMAIN))

class WithDrawalTransactionInLine(admin.StackedInline):
    model=WithDrawalTransaction
    list_display = ['id','sender','receiving_address','value_in_btc','value_in_cad','status',
    'network_fees_in_btc','is_otp_verfied','created_date','reference_number','related_transaction']
    readonly_fields=['created_date']
    def has_module_permission(self,request,obj=None):
        return True
    def has_change_permission(self,request,obj=None):
        return False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True    


class STBTransactionInLine(admin.StackedInline):
    model=STBTransaction
    fk_name='sender'
    list_display = ['id','sender','receiver','value','value_in_cad','status','transaction_type','is_otp_verfied',
    'is_validated','error_message','error_code','created_date','wallet_activation_charge',
    'reference_number']
    def has_module_permission(self,request,obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False

class xrplWalletAdmin(admin.ModelAdmin):
    fields=['user','account_id','key_type','is_funded','is_trust_line_set','is_master_seed_noted_down','xrpl_balance','bitcoin_balance']
    list_display = ['id','user','account_id','payid','master_seed','xrpl_balance','bitcoin_balance','is_funded','is_trust_line_set']
    # list_display = ['id','user','account_id','payid','trust_line_button','xrpl_balance','bitcoin_balance','is_funded','is_trust_line_set']
    search_fields = ('account_id','user__username')
    # readonly_fields=['trust_line_button',]
    inlines=[STBTransactionInLine,WithDrawalTransactionInLine]

    def has_module_permission(self,request,obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        # return True if request.user.user_type=="superadmin" else False
        try:
            return True if request.user.is_superuser else False
        except:
            return False
    def has_add_permission(self, request, obj=None):
        # return False
        try:
            return True if request.user.is_superuser else False
        except:
            return False
    def has_change_permission(self, request, obj=None):
        return False



    def payid(self,obj):
        user_name = obj.user.username
        try:
            payid = get_payid_uri(user_name)
            return payid
        except:
            return None
 
class FundingTransactionResouce(resources.ModelResource):
    user = fields.Field(column_name='user',attribute='user',widget=ForeignKeyWidget(User,'username'))
    class Meta:
        model=FundingTransaction

class FundingTransactionAdmin(ExportMixin,admin.ModelAdmin):
    list_display = ['id','user','value_in_cad','value','commission','activation_fee','received','status','confirmations','created_date','transaction_verfied','error_code','error_message','reference_number']
    list_filter = (('user',admin.RelatedOnlyFieldListFilter ),('created_date', DateRangeFilter))
    resource_class=FundingTransactionResouce
  
    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True
    def has_change_permission(self,request,obj=None):
        return False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True if request.user.is_superuser else False

class BitcoinWalletAccountAdmin(admin.ModelAdmin):
    fields=['user','xpub','xpriv','balance','index']
    list_display = ['id','user','bitcoin_address','balance','index']
    search_fields = ('user__username',)
    # readonly_fields=['user','balance']
    def has_view_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_module_permission(self,request,obj=None):
        return True
    def has_change_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
        
    def bitcoin_address(self,obj):
        receiving_address_obj = obj.receiving_address
        address = receiving_address_obj.address
        return address




class STBTransactionResouce(resources.ModelResource):
    sender = fields.Field(column_name='sender',attribute='sender',widget=ForeignKeyWidget(xrplWallet,'user'))
    receiver = fields.Field(column_name='receiver',attribute='receiver',widget=ForeignKeyWidget(xrplWallet,'user'))
    related_funding_transaction=fields.Field(column_name='related_funding_transaction',attribute='related_funding_transaction',widget=ForeignKeyWidget(FundingTransaction,'user'))
    class Meta:
        model=STBTransaction

    def has_view_permission(self,request,obj=None):
        return True if request.user.is_superuser else False

class STBTransactionAdmin(ExportMixin,admin.ModelAdmin):
    resource_class=STBTransactionResouce
    list_display = ['id','sender','receiver','value','value_in_cad','status','transaction_type','is_otp_verfied',
    'is_validated','error_message','error_code','created_date','wallet_activation_charge','reference_number']
    list_filter = (
       ('sender',admin.RelatedOnlyFieldListFilter ),('receiver',admin.RelatedOnlyFieldListFilter ),
        ('created_date', DateRangeFilter),'transaction_type'
    )
    readonly_fields=['created_date']

    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True
    def has_change_permission(self,request,obj=None):
        return False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True if request.user.is_superuser else False 
 
class IssuerWalletAdmin(admin.ModelAdmin):
    list_display = ['id','wallet','address','bitcoin_balance','xrpl_balance']
    def bitcoin_balance(self,obj):
        issuer_wallet_obj = obj.wallet
        balance = issuer_wallet_obj.bitcoin_balance
        return balance
    def xrpl_balance(self,obj):
        issuer_wallet_obj = obj.wallet
        balance = issuer_wallet_obj.xrpl_balance
        return balance
    def address(self,obj):
        issuer_wallet_obj = obj.wallet
        xrpl_address = issuer_wallet_obj.account_id
        return xrpl_address
    def has_delete_permission(self, request, obj=None):
        return False


class CommissionWalletAdmin(admin.ModelAdmin):
    list_display = ['id','wallet','address','bitcoin_balance','xrpl_balance']
    def bitcoin_balance(self,obj):
        issuer_wallet_obj = obj.wallet
        balance = issuer_wallet_obj.bitcoin_balance
        return balance
    def xrpl_balance(self,obj):
        issuer_wallet_obj = obj.wallet
        balance = issuer_wallet_obj.xrpl_balance
        return balance
    def address(self,obj):
        issuer_wallet_obj = obj.wallet
        xrpl_address = issuer_wallet_obj.account_id
        return xrpl_address
    def has_delete_permission(self, request, obj=None):
        return False
    
class AppConfigurationAdmin(admin.ModelAdmin):
    list_display = ['id','name','current_reference_number',
    'current_withdraw_reference_number','minimum_xrpl_balance',
    'minimum_bitcoin_balance',]



class TransactionOtpAttemptAdmin(admin.ModelAdmin):
    list_display = ['id','transaction_id','user','no_of_unsuccessful_attempts',
    'is_successful_attempt','created_date','modified_date']


    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True

class MinimumbalanceAdmin(admin.ModelAdmin):
    list_display = ['minimum_xrpl_balance','minimum_bitcoin_balance','send_email_to','active'
    ]



class AppNotificationAdmin(admin.ModelAdmin):
    list_display = ['id','message','activation_actions','sent_time']


    def publish_message(self, request,app_notification_id, *args, **kwargs):
        logger.info(request.META['HTTP_REFERER'])
        app_notification_obj = self.get_object(request,app_notification_id)
        message =  app_notification_obj.message


        ios_devices = APNSDevice.objects.all()
        logger.info("ios_devices are ",ios_devices)
        if ios_devices.count()!=0:
            for ios_device in ios_devices:
                try:
                    ios_devices.send_message(message)
                except Exception as e:
                    logger.info("error in line 229 for ios is",e)
                    continue
        app_notification_obj.sent_time = now()
        app_notification_obj.is_published = True
        app_notification_obj.save()

        logger.info("came in 108")
        return HttpResponseRedirect(request.META['HTTP_REFERER'])




    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^(?P<app_notification_id>.+)/publish/$',
                self.admin_site.admin_view(self.publish_message),
                name='publish-message',
            ),

        ]

        return custom_urls + urls

    def activation_actions(self, obj):
        logger.info('objects=',obj)
        if obj.is_published:
            return format_html(

                # '<a class="button" style="background-color: #bfbdbd; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Deactivate All</a>&nbsp;&nbsp;'
                '<a class="button disabled" style="background-color: #bfbdbd; cursor: not-allowed; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Published</a>',
                # reverse('admin:deactivate-coupons', args=[obj.pk]),
                reverse('admin:publish-message', args=[obj.pk]),
            )
        else:
            return format_html(

                # '<a class="button" style="background-color: #bfbdbd; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Deactivate All</a>&nbsp;&nbsp;'
                '<a class="button" style="background-color: #70ccea; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Publish</a>',
                # reverse('admin:deactivate-coupons', args=[obj.pk]),
                reverse('admin:publish-message', args=[obj.pk]),
            )
    activation_actions.short_description = 'Publish'
    activation_actions.allow_tags = True

    def suit_row_attributes(self, obj, request):
        if obj.is_published:
            class_map = {obj.is_published: 'table-success',}
        else:
            class_map = {obj.is_published: 'table-danger',}
        css_class = class_map.get(obj.is_published)
        if css_class:
            return {'class': css_class}


class PendingTransactionsAdmin(admin.ModelAdmin):
    list_display = ['receiver','sender','transaction_id','is_completed']

    def has_view_permission(self, request, obj=None):
        return True
    def has_module_permission(self, request, obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False



class PendingFundTransactionsAdmin(admin.ModelAdmin):
    list_display = ['receiver','transaction_id','is_completed','value']


    def has_view_permission(self, request, obj=None):
        return True
    def has_module_permission(self, request, obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False



class CommissionAdmin(admin.ModelAdmin):
    list_display = ['name','Percentage_Commission_for_wallet_Transactions',
    'Percentage_Commission_for_Fund_Transactions','active',]


    def Percentage_Commission_for_wallet_Transactions(self,obj):
        transaction_commision = obj.transaction_commision
        transaction_commision = '{:.2f}'.format(transaction_commision)
        return transaction_commision

    def Percentage_Commission_for_Fund_Transactions(self,obj):
        fund_wallet_commision = obj.fund_wallet_commision
        fund_wallet_commision = '{:.2f}'.format(fund_wallet_commision)
        return fund_wallet_commision
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['currency','date_time','rate']
    list_filter = [('currency',admin.RelatedOnlyFieldListFilter),]

    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_change_permission(self,request,obj=None):
        return True
    def has_add_permission(self,request,obj=None):
        return True
    def has_delete_permission(self,request,obj=None):
        return True

class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['id','name','code']

    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_change_permission(self,request,obj=None):
        return True
    def has_add_permission(self,request,obj=None):
        return True
    def has_delete_permission(self,request,obj=None):
        return True

class AdminEmailAdmin(admin.ModelAdmin):
    list_display = ['id','email','active']
    list_editable = ('active',)
class FundingAddressAdmin(admin.ModelAdmin):
    list_display=('address','bitcoin_account','receiveIndex',)
    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self,request,obj=None):
        return True
    def has_delete_permission(self,request,obj=None):
        return True
admin.site.register(xrplWallet,xrplWalletAdmin)
admin.site.register(BitcoinWalletAccount,BitcoinWalletAccountAdmin)
admin.site.register(FundingAddress,FundingAddressAdmin)
admin.site.register(Commission,CommissionAdmin)
admin.site.register(FundingTransaction,FundingTransactionAdmin)
admin.site.register(STBTransaction,STBTransactionAdmin)
admin.site.register(CentralWallet,IssuerWalletAdmin)
admin.site.register(CommissionWallet,CommissionWalletAdmin)
admin.site.register(AppConfiguration,AppConfigurationAdmin)

admin.site.register(TransactionOtpAttempt,TransactionOtpAttemptAdmin)
admin.site.register(Minimumbalance,MinimumbalanceAdmin)
admin.site.register(AdminEmail,AdminEmailAdmin)

admin.site.register(PendingTransactions,PendingTransactionsAdmin)
admin.site.register(PendingFundTransactions,PendingFundTransactionsAdmin)
admin.site.register(AppNotification,AppNotificationAdmin)
admin.site.register(ExchangeRate,ExchangeRateAdmin)

admin.site.register(Currency,CurrencyAdmin)