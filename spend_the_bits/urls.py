
from django.contrib import admin
from django.urls import path,include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from payid import views as v2
from accounts.views import LoginView

from django.conf import settings
from django.conf.urls.static import static
from two_factor.urls import urlpatterns as tf_urls
from  payid.views import ParsePayid
from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls

from two_factor.admin import AdminSiteOTPRequired

admin.site.site_header = "SpendTheBits"
admin.site.site_title = "SpendTheBits Admin Portal"
admin.site.index_title = "Welcome to SpendTheBits Admin Portal"

# otp_admin_site = AdminSiteOTPRequired()
urlpatterns = [
#TODO : Add URL Endpoint
]
