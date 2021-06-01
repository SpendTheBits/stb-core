from django.contrib import admin
from withdraw.models import *

from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter


from django.conf.urls import url
from django.urls import reverse
from django.http import HttpResponseRedirect
from push_notifications.models import APNSDevice, GCMDevice
from django.utils.timezone import now
from django.utils.html import format_html
from ripple_wallet.ripple_utils import update_all_ripple_accounts,update_ripple_account
from ripple_wallet.models import Currency
from django.conf import settings
from .withdrawal_transaction import decline_withdrawal_transaction,approve_withdrawal_transaction
import threading
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ExportActionModelAdmin,ExportMixin
from import_export import fields, resources

class WidthdrwalTransactionResouce(resources.ModelResource):
    sender = fields.Field(column_name='user',attribute='user',widget=ForeignKeyWidget(RippleWallet,'user'))
    # receiver = fields.Field(column_name='receiver',attribute='receiver',widget=ForeignKeyWidget(RippleWallet,'user'))
    related_transaction=fields.Field(column_name='related_transaction',attribute='related_transaction',widget=ForeignKeyWidget(STBTransaction,'reference_number'))
    refund_transaction=fields.Field(column_name='refund_transaction',attribute='refund_transaction',widget=ForeignKeyWidget(STBTransaction,'reference_number'))
    
    class Meta:
        model=WithDrawalTransaction


class WithDrawalTransactionAdmin(ExportMixin,admin.ModelAdmin):
    list_display = ['id','sender','receiving_address','value_in_btc','value_in_cad','status',
    'network_fees_in_btc','is_otp_verfied',
    'created_date',
    'reference_number','related_transaction']
    list_filter = (
       ('sender',admin.RelatedOnlyFieldListFilter ),
        ('created_date', DateRangeFilter),
    )
    resource_class=WidthdrwalTransactionResouce
    def has_module_permission(self,request,obj=None):
        return True
    def has_view_permission(self, request, obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        try:
            return True if request.user.user_type=="superadmin" else False
        except:
            return True
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False

class WithdrawLimitAdmin(admin.ModelAdmin):
    list_display = ['id','limit_in_btc','limit_in_cad','active']


    def limit_in_cad(self,obj):
        limit_in_btc = obj.limit_in_btc
        limit_in_cad = Currency.get_equivalent_amount_in_cad(limit_in_btc,"BTC")

        return limit_in_cad

    def has_delete_permission(self, request, obj=None):
        return False

class WithdrawTransactionOtpAttemptAdmin(admin.ModelAdmin):
    list_display = ['transaction_id','user','no_of_unsuccessful_attempts','is_successful_attempt']
 
    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


class NetworkFeesAdmin(admin.ModelAdmin):
    list_display = ['satoshi_per_bytes_for_fund_transaction','transaction_size_in_bytes_for_fund_transaction',
    'satoshi_per_bytes_for_withdraw_transaction','transaction_size_in_bytes_for_withdraw_transaction',
    'active']





class WithdrawApprovalAdmin(admin.ModelAdmin):
    list_display = ['id','ripple_wallet','value_in_btc','value_in_cad',
    'activation_actions',
        ]

    def approve_transaction(self, request,withdraw_approval_object_id, *args, **kwargs):
        logger.info(request.META['HTTP_REFERER'])
        withdraw_approval_object = self.get_object(request,withdraw_approval_object_id)


        # withdraw_approval_object.approved_or_declined_by = now()
        withdraw_approval_object.is_approved = True
        withdraw_approval_object.save()

        withdraw_transaction_obj = withdraw_approval_object.withdraw_transaction
        logger.info("withdraw_transaction_obj @65 is",withdraw_transaction_obj)
        thread1 = threading.Thread(target=approve_withdrawal_transaction, args=(withdraw_transaction_obj,))
        thread1.start()

        return HttpResponseRedirect(request.META['HTTP_REFERER'])


    def decline_transaction(self, request,withdraw_approval_object_id, *args, **kwargs):
        logger.info(request.META['HTTP_REFERER'])
        withdraw_approval_object = self.get_object(request,withdraw_approval_object_id)

        withdraw_approval_object.sent_time = now()
        withdraw_approval_object.is_declined = True
        withdraw_approval_object.save()
        withdraw_transaction_obj = withdraw_approval_object.withdraw_transaction
        logger.info("withdraw_transaction_obj @80 is",withdraw_transaction_obj)
        thread1 = threading.Thread(target=decline_withdrawal_transaction, args=(withdraw_transaction_obj,))
        thread1.start()

        return HttpResponseRedirect(request.META['HTTP_REFERER'])




    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^(?P<withdraw_approval_object_id>.+)/approve_transaction/$',
                self.admin_site.admin_view(self.approve_transaction),
                name='approve_transaction',
            ),
            url(
                r'^(?P<withdraw_approval_object_id>.+)/decline_transaction/$',
                self.admin_site.admin_view(self.decline_transaction),
                name='decline_transaction',
            ),
        ]

        return custom_urls + urls

    def activation_actions(self, obj):
        logger.info('objects=',obj)
        if obj.is_declined is None and obj.is_approved is None:
            return format_html(


                # '<a class="button" style="background-color: #bfbdbd; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Deactivate All</a>&nbsp;&nbsp;'
                '<a class="button" style="background-color: #70ccea; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Approve</a>'
                '<a class="button" style="background-color: red; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Reject</a>',
                # reverse('admin:deactivate-coupons', args=[obj.pk]),
                reverse('admin:approve_transaction', args=[obj.pk]),


                # reverse('admin:deactivate-coupons', args=[obj.pk]),
                reverse('admin:decline_transaction', args=[obj.pk]),
            )
        elif obj.is_declined is True:
            return format_html(

                # '<a class="button" style="background-color: #bfbdbd; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Deactivate All</a>&nbsp;&nbsp;'
                '<a class="button disabled" style="background-color: #bfbdbd; cursor: not-allowed; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Declined</a>',
                # reverse('admin:deactivate-coupons', args=[obj.pk]),
                reverse('admin:approve_transaction', args=[obj.pk]),

            )
        elif obj.is_approved is True:
            return format_html(

                # '<a class="button" style="background-color: #bfbdbd; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Deactivate All</a>&nbsp;&nbsp;'
                '<a class="button disabled" style="background-color: #bfbdbd; cursor: not-allowed; border: none;color: black;padding: 10px 12px;text-align: center;text-decoration: none;display: inline-block;font-size: 12px;" href="{}">Approved</a>',
                # reverse('admin:deactivate-coupons', args=[obj.pk]),
                reverse('admin:approve_transaction', args=[obj.pk]),

            )

    activation_actions.short_description = 'Admin Action'
    activation_actions.allow_tags = True


class LedgerAdmin(admin.ModelAdmin):
    list_display = ['id','user','amount','currency','particulars','notes',
    'reference_number','created_date']
    list_filter = (
       ('user',admin.RelatedOnlyFieldListFilter ),
        'notes','reference_number',('created_date', DateRangeFilter),
    )

    def has_module_permission(self,request,obj=None):
        try:
            return True if request.user.user_type=="superadmin" else False
        except:
            return True
    def has_change_permission(self,request,obj=None):
        return False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True


class BitcoinNetworkLedgerAdmin(admin.ModelAdmin):
    list_display = ['id','sending_address','receiving_address','amount','sender_user','receiver_user',
    'particulars','notes','reference_number','created_date']
    list_filter = (
       ('sender_user',admin.RelatedOnlyFieldListFilter ),
       ('receiver_user',admin.RelatedOnlyFieldListFilter ),
        ('created_date', DateRangeFilter),'reference_number'
    )


    def has_delete_permission(self, request, obj=None):
        return True if request.user.user_type=="superadmin" else False
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(WithDrawalTransaction,WithDrawalTransactionAdmin)
admin.site.register(WithdrawTransactionOtpAttempt,WithdrawTransactionOtpAttemptAdmin)
admin.site.register(WithdrawApproval,WithdrawApprovalAdmin)
admin.site.register(WithdrawLimit,WithdrawLimitAdmin)
admin.site.register(NetworkFees,NetworkFeesAdmin)
admin.site.register(Ledger,LedgerAdmin)
admin.site.register(BitcoinNetworkLedger,BitcoinNetworkLedgerAdmin)

