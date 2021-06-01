from .models import AdminEmail
from accounts.utils import send_mail
import requests

from accounts.models import User,UserProfile

from django.conf import settings
from withdraw.models import *


def related_transaction_transfer_failed_email(transaction_obj):

    transaction_type = transaction_obj.transaction_type

    main_transaction_obj = transaction_obj.related_transaction
    admin_email_list = AdminEmail.objects.filter(active=True)
    context = {
    'id':transaction_obj.id,
    'transaction_type':transaction_type,
    'main_transaction_id': main_transaction_obj.id,
    'value_in_cad': transaction_obj.value_in_cad
    }

    html_address = 'email/related_transaction_transfer_failed_email.html'
    text_address = 'email/txt/related_transaction_transfer_failed_email.txt'
    subject = "Related Transaction Transfer Failed"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)





    return



def issue_btc_to_stb_wallet_failed(fund_transaction_obj,stb_transaction_obj):


    admin_email_list = AdminEmail.objects.filter(active=True)
    context = {
   
    "fund_transaction_id":fund_transaction_obj.id
    }

    html_address = 'email/issue_btc_to_stb_wallet_failed.html'
    text_address = 'email/txt/issue_btc_to_stb_wallet_failed.txt'
    subject ="Transfer Of Issued BTC on Funding Failed"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)





    return


def pep_user_signed(user):

    user_profile_obj = UserProfile.objects.get(user=user)
    date_joined = user.date_joined
    date_joined = date_joined.strftime('%Y/%m/%d')
    dob = user_profile_obj.dob
    
    username = user.username
    user_email = user.email
    name = user_profile_obj.name
    nation = user_profile_obj.nation.name
    pincode = user_profile_obj.pincode
    occupation = user_profile_obj.occupation
    phone_number = user_profile_obj.phone_number

    admin_email_list = AdminEmail.objects.filter(active=True)

    if settings.PRODUCTION_ENV:
        server = "prod_server"
    else:
        server = "test_server"
    context = {
    'server':server,
    'username':username,
    'user_email':user_email,
    'name':name,
    'nation':nation,
    'pincode':pincode,
    'dob':dob,
    'date_joined':date_joined,
    'phone_number':phone_number,
    'occupation':occupation





    }

    html_address = 'email/pep_user_signed.html'
    text_address = 'email/txt/pep_user_signed.txt'
    subject = "PEP User signed"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)





    return


def withdraw_transaction_request_admin_mail(withdraw_transaction_object):
    value_in_btc = withdraw_transaction_object.value_in_btc
    value_in_cad = withdraw_transaction_object.value_in_cad
    created_date = withdraw_transaction_object.created_date
    user = withdraw_transaction_object.sender.user
    user_profile_obj = UserProfile.objects.get(user=user)

    created_date = created_date.strftime('%Y/%m/%d')

    
    username = user.username
    user_email = user.email
    name = user_profile_obj.name
    nation = user_profile_obj.nation.name
    pincode = user_profile_obj.pincode
    occupation = user_profile_obj.occupation
    phone_number = user_profile_obj.phone_number

    admin_email_list = AdminEmail.objects.filter(active=True)

    if settings.PRODUCTION_ENV:
        server = "prod_server"
    else:
        server = "test_server"
    context = {
    'server':server,
    'username':username,
    'user_email':user_email,
    'name':name,
    'nation':nation,
    "value_in_btc":value_in_btc,
    'value_in_cad':value_in_cad,
    'created_date':created_date,



    'phone_number':phone_number,
    'occupation':occupation





    }

    html_address = 'email/withdraw_request.html'
    text_address = 'email/txt/withdraw_request.txt'
    subject = "Withdraw Transaction Request"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)





    return




def refund_failed(fund_transaction_obj,stb_transaction_obj):


    admin_email_list = AdminEmail.objects.filter(active=True)
    context = {
   
    "fund_transaction_id":fund_transaction_obj.id
    }

    html_address = 'email/refund_failed.html'
    text_address = 'email/txt/refund_failed.txt'
    subject ="Refund Failed"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)





    return




def xrp_transfer_failed(fund_transaction_obj,stb_transaction_obj):


    admin_email_list = AdminEmail.objects.filter(active=True)
    context = {
   
    "fund_transaction_id":fund_transaction_obj.id
    }

    html_address = 'email/refund_failed.html'
    text_address = 'email/txt/refund_failed.txt'
    subject ="Refund Failed"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)





    return






def send_btc_to_cold_wallet_email(amount):
    admin_email_list = AdminEmail.objects.filter(active=True)
    context = {
   
    "fund_transaction_id":fund_transaction_obj.id
    }

    html_address = 'email/refund_failed.html'
    text_address = 'email/txt/refund_failed.txt'
    subject ="Refund Failed"

    for admin_email in admin_email_list:
        send_mail(admin_email,subject,context,html_address,text_address)
    return

