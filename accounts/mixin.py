from django.conf import settings
from itertools import chain



class ReadOnlyAdminMixin(object):

    def has_change_permission(self, request, obj=None):
        if settings.PRODUCTION_ENV:
            return True
        else:
            return True

    def has_add_permission(self, request):
        if settings.PRODUCTION_ENV:
            return True
        else:
            return True

    def has_delete_permission(self, request, obj=None):
        if settings.PRODUCTION_ENV:
            return True
        else:
            return True

