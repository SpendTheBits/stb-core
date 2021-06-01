import requests
import random
from accounts.models import *
from django.core.mail import send_mail
from django.conf import settings
from ripple_wallet.models import AdminEmail
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes,force_text
from django.contrib.sites.shortcuts import get_current_site
from rest_framework.decorators import api_view,permission_classes
from django.template.loader import render_to_string
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework_simplejwt.tokens import RefreshToken
from authy.api import AuthyApiClient
from push_notifications.models import APNSDevice, GCMDevice
authy_api = AuthyApiClient(settings.ACCOUNT_SECURITY_API_KEY)

from urllib.parse import urlparse
# from urlparse import urlparse  # Python 2

from twilio.rest import Client


account_sid = settings.TWILIO_ACCOUNT_SID
auth_token = settings.TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)


class TokenGenerator(PasswordResetTokenGenerator):
      pass

account_activation_token = TokenGenerator() 

def get_host_from_url(url):
    parsed_uri = urlparse(url)
    try:
        return parsed_uri.netloc
    except Exception as e:
        logger.info("ERROR IN PRSING URL:",str(e))
        return ""
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def send_mail(receiver_email,subject,context,html_address,text_address):

    logger.info("context",context)

    email_html_message = render_to_string(html_address, context)
    email_plaintext_message = render_to_string(text_address, context)
                
    logger.info("receiver_email  is",receiver_email)
    msg = EmailMultiAlternatives(
    (subject),
    email_plaintext_message,
    settings.FROM_EMAIL,
    [receiver_email,]
    )
    msg.attach_alternative(email_html_message, "text/html")
    try:
        msg.send()
        logger.info("sent mail worked thats why came here")
    except Exception as e:
        logger.info("error in sending mail in @284 is",e)

    return


def send_mail_for_any_problem(instance):
    to_mail='sushantamandal91@gmail.com'
    html_addr='email/register_email.html'
    text_address = 'email/common_text.txt'
    subject="Problem query"
    context={
        "name":instance.user.username,
        "image":instance.image.url if instance.image else None
    }
    send_mail(to_mail,subject,context,html_addr,text_address)
    return

def send_mail_for_register(instance):
    to_mail=instance.email
    html_addr='email/register_email.html'
    text_address = 'email/common_text.txt'
    subject_user="Welcome to SpendTheBits"
    logger.info('call for registation')
    context={
        "name":instance.username
    }
    to_admin_mail=AdminEmail.objects.all().first().email
    admin_html_addr='email/register_email_to_admin.html'
    subject_admin="New user is registered"
    send_mail(to_mail,subject,context,html_addr,text_address)
    send_mail(to_admin_mail,subject_admin,context,admin_html_addr,text_address)
    
    return

def send_mail_for_transaction(transaction_obj):
    to_mail=transaction_obj.sender.user.email
    html_addr='email/transaction_email.html'
    text_address = 'email/common_text.txt'
    subject="Thank you for the transaction"
    logger.info('transaction email')
    context={
        "user":transaction_obj.sender.user.first_name,
        "amount":transaction_obj.value_in_cad
    }
    send_mail(to_mail,subject,context,html_addr,text_address)
    return



def send_otp_to_user(user):
    logger.info("came in sending otp")
    user_profile_obj = UserProfile.objects.get(user=user)

    service_sid = user_profile_obj.service_sid

    phone_number = user_profile_obj.phone_number
    country_code = user_profile_obj.nation.dialing_code

    phone = str(country_code)+str(phone_number)
    app_hash = settings.SMS_APP_HASH
    try:
        sms = client.verify.services(service_sid).verifications.create(to=phone, 
        channel='sms',app_hash=app_hash)
 
    except Exception as e:
        logger.info("error in sending otp is ",e)

    logger.info("otp sent @232")


def send_activation_mail(user):
    try:
        logger.info("came in send activation mail to user")
        logger.info("receiver is",user)
        # logo_obj = Logo.objects.filter(active=True).first()
        current_url = settings.CURRENT_API_URL
        context = {
            #try to use python reveerse method for url
                'name':user.first_name.capitalize(),
                'email_verification_url': str(current_url)+"/v1/accounts/verify_email/?uid={uid}&token={token}".format(
                    uid=urlsafe_base64_encode(force_bytes(user.id)),token=account_activation_token.make_token(user)),
                # 'image_url':current_url + str(logo_obj.image.url)
            }

        html_address = 'email/email_verification.html'
        text_address = 'email/user_reset_password.txt'
        subject = "Spend The Bits Account Verification"
        receiver_email = user.email
        response = send_mail(receiver_email,subject,context,html_address,text_address)
        logger.info("response after send mail function is",response)
        return
    except:
        logger.info("Exception in Sending Activate Mail to ",user.first_name)


def send_notification(user,message):
    logger.info("came in send_notification")
    logger.info("user is",user)
    logger.info("message is",message)
    try:
        android_devices = GCMDevice.objects.filter(user=user)
        for device in android_devices:
            try:
                logger.info("YO ADI::android_devices in send_notification is",device.registration_id)
                device.send_message(message)
            except Exception as e:

                logger.info("YO ADI ::error in sending message for android devices is",e)
                continue
    except Exception as e:
        logger.info("error in sending message for android devices is",e)

    try:
        ios_devices = APNSDevice.objects.filter(user=user)
        logger.info("ios_devices is",ios_devices)
        for ios_device in ios_devices:
            registration_id = ios_device.registration_id
            # token = registration_id
            # alert = message
            logger.info("registration_id is",registration_id)
            try:
                ios_device.send_message(message)
            except Exception as e:
                logger.info(" ADITYAAAA error is",e)
                logger.info("ADITYAAAAAA error occured for registration_id",registration_id)
                continue
    except Exception as e:
        logger.info("error in sending message for apple devices  is",e)
    
    return
