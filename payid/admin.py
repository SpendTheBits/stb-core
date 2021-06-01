from django.contrib import admin
from .models import *
from django.conf import settings
# Register your models here.


def get_payid_uri( name ):
    return ''.join((name.lower(), '$', settings.PAYID_URI_DOMAIN))

class CryptoAddressAdmin(admin.ModelAdmin):
    list_display = ['id','address','paymentNetwork','environment','entity','show',]
    list_filter = ('paymentNetwork','environment',('entity',admin.RelatedOnlyFieldListFilter ),)

class PayIdAdmin(admin.ModelAdmin):
    list_display = ['id','name','memo','user_profile','payid',]
    search_fields = ("user_profile__name",'name')


    def payid(self,obj):
        payid = get_payid_uri(obj.name)


        return payid
admin.site.register(CryptoAddress,CryptoAddressAdmin)
admin.site.register(PayId,PayIdAdmin)