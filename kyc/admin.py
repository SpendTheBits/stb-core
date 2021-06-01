from django.contrib import admin
from .models import * 

class KycErrorAndSuggestInline(admin.StackedInline):
    model=KycApplicationErrorAndSuggest
    def get_extra(self, request, obj=None, **kwargs):
        extra = 1
        return extra
class KycAttemptAdmin(admin.ModelAdmin):
    list_display = ['user','created_date','modified_date']

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
        try:
            return True if request.user.user_type=="superadmin" else False
        except:
            return True


class KycApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_id','status','created_date','modified_date']
    inlines=[KycErrorAndSuggestInline]


admin.site.register(KycApplicationErrorAndSuggest)
admin.site.register(KycAttempt,KycAttemptAdmin)
admin.site.register(KycApplication,KycApplicationAdmin)
