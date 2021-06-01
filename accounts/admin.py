from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from accounts.models import *
from import_export.admin import ExportActionModelAdmin
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from xrpl_wallet.models import xrplWallet
from django.conf import settings
from django.utils.html import format_html
from django.conf.urls import url
from django.urls import reverse
from withdraw.models import *
from accounts.mixin import ReadOnlyAdminMixin
from xrpl_wallet.models import *
import nested_admin



class WithDrawalTransactionInLine(nested_admin.NestedStackedInline):
    model=WithDrawalTransaction
    list_display = ['id','sender','receiving_address','value_in_btc','value_in_cad','status',
    'network_fees_in_btc','is_otp_verfied','created_date','reference_number','related_transaction']
    readonly_fields=['created_date']
    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_change_permission(self,request,obj=None):
        return False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True if request.user.is_superuser else False


class STBTransactionInLine(nested_admin.NestedStackedInline):
    model=STBTransaction
    fk_name='sender'
    list_display = ['id','sender','receiver','value','value_in_cad','status','transaction_type','is_otp_verfied',
    'is_validated','error_message','error_code','created_date','wallet_activation_charge',
    'reference_number']
    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True
    def has_change_permission(self,request,obj=None):
        return False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True    


class FundingTransactionInline(nested_admin.NestedStackedInline):
    model=FundingTransaction
    list_display = ['id','user','value_in_cad','value','commission','activation_fee','received','status',
    'confirmations','created_date','transaction_verfied','error_code','error_message','reference_number']


    def get_readonly_fields(self,request,obj=None):
        return []
        
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

class UserProfileInline(nested_admin.NestedStackedInline):
    model = UserProfile
    def has_view_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
        
    def has_module_permission(self,request,obj=None):
        logger.info('user obj=',obj)
        return True if obj is not None and request.user.is_superuser else False
    def has_change_permission(self,request,obj=None):
        return settings.TEST_ENV
    def has_add_permission(self,request,obj=None):
        return settings.TEST_ENV
    def has_delete_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    
class BitcoinwalletInline(nested_admin.NestedStackedInline):
    model=BitcoinWalletAccount
    # readonly_fields=['balance','index']
    def get_readonly_fields(self,request,obj=None):
        if request.user.is_superuser:
            return ['balance','index']

        return ['xpub','xpriv','index','balance',]
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
        




class BitcoinNetworkLedgerInline(nested_admin.NestedStackedInline):
    model=BitcoinNetworkLedger
    list_display = ['id','sending_address','receiving_address','amount','sender_user','receiver_user',
    'particulars','notes','reference_number','created_date']
    fk_name='sender_user'
    # def has_module_permission(self,request,obj=None):
    #     return True
    # def has_change_permission(self,request,obj=None):
    #     return False
    # def has_add_permission(self,request,obj=None):
    #     return False
    # def has_delete_permission(self,request,obj=None):
    #     return True    
    def has_view_permission(self,request,obj=None):
        return True
    def has_module_permission(self,request,obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


class STBWalletInline(nested_admin.NestedStackedInline):
    model = xrplWallet
    fields=['user','account_id','key_type','is_funded','master_seed','master_seed_hex','is_trust_line_set','is_master_seed_noted_down','xrpl_balance','bitcoin_balance']
    # readonly_fields=['account_id','key_type','is_funded','is_trust_line_set','is_master_seed_noted_down','xrpl_balance','bitcoin_balance']
    inlines=[WithDrawalTransactionInLine,STBTransactionInLine]

    def get_readonly_fields(self,request,obj=None):
        if request.user.is_superuser:
            return ['account_id','key_type','is_funded','is_trust_line_set','is_master_seed_noted_down','xrpl_balance','bitcoin_balance']
        else:
            return ['account_id','key_type','is_funded','is_trust_line_set','master_seed','master_seed_hex','is_master_seed_noted_down','xrpl_balance','bitcoin_balance']

    # def has_module_permission(self,request,obj=None):
    #     return True
    # def has_change_permission(self,request,obj=None):
    #     return True
    # def has_add_permission(self,request,obj=None):
    #     return False
    # def has_delete_permission(self,request,obj=None):
    #     return True    
    def has_view_permission(self,request,obj=None):
        return True 
    def has_module_permission(self,request,obj=None):
        return True 
    def has_change_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_add_permission(self,request,obj=None):
        return False
    def has_delete_permission(self,request,obj=None):
        return True if request.user.is_superuser else False

class UserAdmin(DjangoUserAdmin,nested_admin.NestedModelAdmin):
    list_display = ("id",'email','username','phone_number','nation','currency','phone_verfied',
    'email_verfied','date_joined','is_staff','user_type','is_freezed','is_active','is_politically_exposed')
    # here in fieldsets we add the fields which users can see in admin panel
    fieldsets = (
        (None, {'fields': ('email','username','password','phone_verfied','email_verfied','is_freezed','user_type',
        'is_active',)}),
        # ('Personal info', {'fields': ('',)}),
        # ('Permissions', {'fields': ('',)}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    # this field will be asked when creating a user in admin panel
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username','password1', 'password2','user_type')}
        ),
    )
    ordering = ('-date_joined',)
    search_fields = ('id','email','username')
    list_filter=('user_type',)
    list_editable = ('is_freezed','is_active','phone_verfied','email_verfied',)
    # inlines = [UserProfileInline,BitcoinwalletInline,STBWalletInline,FundingTransactionInline,BitcoinNetworkLedgerInline]
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        else:
            return ['user_type',]

    def get_exclude(self, request, obj=None):
        
        if not request.user.is_superuser:
            return ['user_type',]
        else:
            return []
        
    def get_inlines(self, request, obj=None):
        logger.info('user obj=',obj)

        if request.user.is_superuser:
            return [UserProfileInline,BitcoinwalletInline,STBWalletInline,FundingTransactionInline,BitcoinNetworkLedgerInline] 
        else:
            return []
        
    
    # def get_inline_instances(self, request, obj=None):
    #     if obj:
    #         return [UserProfileInline,BitcoinwalletInline,STBWalletInline,FundingTransactionInline,BitcoinNetworkLedgerInline]
    #     else:
    #         return []
    #     return super(UserAdmin, self).get_inline_instances(request, obj)
    def save_model(self, request, obj, form, change):
        # if request.user.is_superuser:
        obj.is_staff = True if obj.user_type is not None or obj.is_staff else False
        obj.is_superuser=True if obj.user_type=="superadmin" or obj.is_superuser else False
        obj.save()

    


    def phone_number(self, obj):
        return obj.user_profile.phone_number

    def nation(self, obj):
        return obj.user_profile.nation

    def currency(self, obj):
        return obj.user_profile.currency_obj

    def is_politically_exposed(self, obj):
        return obj.user_profile.is_politically_exposed

    def has_module_permission(self,request,obj=None):
        # logger.info('check user',request.user)
        return True
    def has_view_permission(self,request,obj=None):
        # logger.info('check user',request.user)
        return True
    def has_delete_permission(self, request, obj=None):
        # return True if request.user.user_type=="superadmin" else False
        try:
            return True if request.user.is_superuser else False
        except:
            return True
        # return True
    def has_add_permission(self, request, obj=None):
        try:
            return True if request.user.is_superuser else False
        except:
            return True
    def has_change_permission(self, request, obj=None):
        try:
            return True if request.user.is_superuser else False
        except:
            return True
    # def get_queryset(self, request):
    #     qs = super(UserAdmin, self).get_queryset(request)
    #     # return qs.filter(is_superuser=False,is_staff=False)
    #     return qs.filter(is_superuser=False,is_staff=False)


        # if settings.PRODUCTION_ENV:
        #     return True
        # else:
        #     return True
    # search_fields = ('id','email','user_profile__phone_number','username')

    # def phone(self,obj):
    #     user_profile_obj = obj.user_profile
    #     phone_num = user_profile_obj.phone_number
    #     return phone_num

    # if settings.PRODUCTION_ENV:
    #     readonly_fields = ('email','username','password','phone_verfied','email_verfied')


# class adminUserAdmin(DjangoUserAdmin,nested_admin.NestedModelAdmin):
#     list_display = ("id",'email','username','date_joined','is_staff','user_type','is_active',)
#     list_filter=['is_active',]
#     # here in fieldsets we add the fields which users can see in admin panel
#     fieldsets = (
#         (None, {'fields': ('email','username','first_name','last_name','is_active',)}),
#         ('Personal info', {'fields': ('user_type',)}),
#         # ('Permissions', {'fields': ('',)}),
#     )
    
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'username','password1', 'password2',)}
#         ),
#     )
#     ordering = ('-date_joined',)
#     search_fields = ('id','email','username','first_name','last_name',)
#     # readonly_fields=('user_type',)
#     exclude=('phone_verfied','email_verfied','is_freezed',)
#     def get_readonly_fields(self, request, obj=None):
#         if obj:
#             return ['user_type']
#         return []

#     # list_editable = ('is_freezed','is_active','phone_verfied','email_verfied',)
#     def save_model(self, request, obj, form, change):
#         # if request.user.is_superuser:
#         obj.is_staff = True
#         obj.user_type="admin"
#         obj.is_superuser=False
#         obj.save()

#     def phone_number(self, obj):
#         return obj.user_profile.phone_number

#     def nation(self, obj):
#         return obj.user_profile.nation

#     def currency(self, obj):
#         return obj.user_profile.currency_obj

#     def is_politically_exposed(self, obj):
#         return obj.user_profile.is_politically_exposed
#     def has_module_permission(self, request, obj=None):
#         return True
#     def has_delete_permission(self, request, obj=None):
#         # return True if request.user.user_type=="superadmin" else False
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#     def has_add_permission(self, request, obj=None):
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#         # return True if request.user.user_type=="superadmin" else False
#     def has_change_permission(self, request, obj=None):
#         # return True if request.user.user_type=="superadmin" else False
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#     def get_queryset(self, request):
#         qs = super(adminUserAdmin, self).get_queryset(request)
#         return qs.filter(user_type="admin")
        



# class SuperadminUserAdmin(DjangoUserAdmin,nested_admin.NestedModelAdmin):
#     list_display = ("id",'email','username','date_joined','is_staff','user_type','is_active',)
#     list_filter=['is_active',]
#     # here in fieldsets we add the fields which users can see in admin panel
#     fieldsets = (
#         (None, {'fields': ('email','username','first_name','last_name','is_active',)}),
#         ('Personal info', {'fields': ('user_type',)}),
#         # ('Permissions', {'fields': ('',)}),
#     )
    
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'username','password1', 'password2',)}
#         ),
#     )
#     ordering = ('-date_joined',)
#     search_fields = ('id','email','username','first_name','last_name',)
#     # readonly_fields=('user_type',)
#     exclude=('phone_verfied','email_verfied','is_freezed',)
#     # inlines = [UserProfileInline,BitcoinwalletInline,STBWalletInline,FundingTransactionInline,BitcoinNetworkLedgerInline]

#     def get_inlines(self, request, obj):
#         if request.user.user_type=="superadmin":
#             return [UserProfileInline,BitcoinwalletInline,STBWalletInline,FundingTransactionInline,BitcoinNetworkLedgerInline]
#         else:
#             return []
#     def get_readonly_fields(self, request, obj=None):
#         if obj:
#             return ['user_type']
#         return []

#     # list_editable = ('is_freezed','is_active','phone_verfied','email_verfied',)
#     def save_model(self, request, obj, form, change):
#         obj.is_staff = True
#         obj.user_type="superadmin"
#         obj.is_superuser=True
#         obj.save()

#     def phone_number(self, obj):
#         return obj.user_profile.phone_number

#     def nation(self, obj):
#         return obj.user_profile.nation

#     def currency(self, obj):
#         return obj.user_profile.currency_obj

#     def is_politically_exposed(self, obj):
#         return obj.user_profile.is_politically_exposed

#     def has_module_permission(self,request,obj=None):
#         return True if request.user.user_type=="support" else False
#     def has_delete_permission(self, request, obj=None):
#         # return True if request.user.user_type=="superadmin" else False
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#     def has_add_permission(self, request, obj=None):
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#         # return True if request.user.user_type=="superadmin" else False
#     def has_change_permission(self, request, obj=None):
#         # return True if request.user.user_type=="superadmin" else False
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#     def get_queryset(self, request):
#         qs = super(SuperadminUserAdmin, self).get_queryset(request)
#         return qs.filter(user_type="superadmin")



# class SupportUserAdmin(DjangoUserAdmin,nested_admin.NestedModelAdmin):
#     list_display = ("id",'email','username','date_joined','is_staff','user_type','is_active',)
#     # here in fieldsets we add the fields which users can see in admin panel
#     fieldsets = (
#         (None, {'fields': ('email','username','first_name','last_name','is_active',)}),
#         ('Personal info', {'fields': ('user_type',)}),
#         # ('Permissions', {'fields': ('',)}),
#     )
    
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'username','password1', 'password2',)}
#         ),
#     )
#     ordering = ('-date_joined',)
#     search_fields = ('id','email','username')
#     # readonly_fields=('user_type',)
#     exclude=('phone_verfied','email_verfied','is_freezed',)
#     def get_readonly_fields(self, request, obj=None):
#         if obj:
#             return ['user_type']
#         return []

#     # list_editable = ('is_freezed','is_active','phone_verfied','email_verfied',)
#     def save_model(self, request, obj, form, change):
#         # if request.user.is_superuser:
#         obj.is_staff = True
#         obj.user_type="support"
#         obj.is_superuser=False
#         obj.save()

#     def phone_number(self, obj):
#         return obj.user_profile.phone_number

#     def nation(self, obj):
#         return obj.user_profile.nation

#     def currency(self, obj):
#         return obj.user_profile.currency_obj

#     def is_politically_exposed(self, obj):
#         return obj.user_profile.is_politically_exposed

#     def has_module_permission(self,request,obj=None):
#         return True
#     def has_delete_permission(self, request, obj=None):
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#         # return True if request.user.user_type=="superadmin" else False
#     def has_add_permission(self, request, obj=None):
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#         # return True if request.user.user_type=="superadmin" else False
#     def has_change_permission(self, request, obj=None):
#         # return True if request.user.user_type=="superadmin" else False
#         try:
#             return True if request.user.user_type=="superadmin" else False
#         except:
#             return False
#     def get_queryset(self, request):
#         qs = super(SupportUserAdmin, self).get_queryset(request)
#         return qs.filter(user_type="support")




# class UserProfileResource(resources.ModelResource):
#     user = fields.Field(
#         column_name='user',
#         attribute='user',
#         widget=ForeignKeyWidget(User, 'email'))

#     class Meta:
#         model = UserProfile
#         export_order = ('id', 'user', )

# class UserProfileAdmin(ReadOnlyAdminMixin,ExportActionModelAdmin):
#     list_display = ['user_id','user','phone_number','nation',"is_politically_exposed"]
#     search_fields = ('user_id','user__email','phone_number','is_politically_exposed')
#     list_display_links  = ('user_id','user',)
#     # if settings.PRODUCTION_ENV:
#     #     readonly_fields=('user','image','phone_number','nation',"is_politically_exposed","currency_obj",
#     #     "on_receive","on_funding","service_sid","name",'address','pincode','dob','occupation','id_document')
#     resource_class = UserProfileResource

#     # def has_delete_permission(self, request, obj=None):
#     #     if settings.PRODUCTION_ENV:
#     #         return True
#     #     else:
#     #         return True
#     def has_module_permission(self,request,obj=None):
#         return True
#     def has_delete_permission(self, request, obj=None):
#         return True if request.user.user_type=="superadmin" else False
#     def has_add_permission(self, request, obj=None):
#         return True if request.user.user_type=="superadmin" else False
#     def has_change_permission(self, request, obj=None):
#         return True if request.user.user_type=="superadmin" else False


class CountryAdmin(ReadOnlyAdminMixin,admin.ModelAdmin):
    list_display = ['id','name','dialing_code','alpha2code','flag_url',"is_default"]
    
    # def has_view_permission(self,request,obj=None):
    #     return True 
    def has_module_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
        
    def has_add_permission(self,request,obj=None):
        return True
    def has_delete_permission(self,request,obj=None):
        return True


class VersionAdmin(admin.ModelAdmin):
    list_display = ['name','release_date','is_active']

    # def has_view_permission(self,request,obj=None):
    #     return True 
    def has_module_permission(self,request,obj=None):
        return True if request.user.is_superuser else False
    def has_change_permission(self,request,obj=None):
        return True 
    def has_add_permission(self,request,obj=None):
        return True
    def has_delete_permission(self,request,obj=None):
        return True 



admin.site.register(User,UserAdmin)
# admin.site.register(UserProfile,UserProfileAdmin)
# admin.site.register(Logo)
admin.site.register(DerogatoryWords)
admin.site.register(Country,CountryAdmin)
admin.site.register(Version,VersionAdmin)
# admin.site.register(Currency)
# admin.site.register(AdminUser,adminUserAdmin)
# admin.site.register(SupportUser,SupportUserAdmin)
# admin.site.register(SuperAdminUser,SuperadminUserAdmin)