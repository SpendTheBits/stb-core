from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.serializers import *
from accounts.models import *
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny
from django.conf import settings
from ripple_wallet.create_ripple_wallet import create_ripple_wallet_and_bitcoin_addresss
from accounts.utils import (send_activation_mail,send_otp_to_user,get_tokens_for_user,get_all_country_details,test_email,
get_currency_codes)
import threading
from ripple_wallet.models import *
from .utils import *
from authy.api import AuthyApiClient
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes,force_text
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from ripple_wallet.helper import get_btc_to_currency
from ripple_wallet.funding_transactions import *
from push_notifications.models import APNSDevice, GCMDevice
authy_api = AuthyApiClient(settings.ACCOUNT_SECURITY_API_KEY)
import datetime
from datetime import timedelta
from django.utils import timezone
import requests
from django.db.models.signals import pre_delete,post_delete
from django.dispatch import receiver

from twilio.rest import Client
from rest_framework.parsers import FormParser, MultiPartParser
from ripple_wallet.admin_notifications import pep_user_signed
from ripple_wallet.models import AppConfiguration,Currency,ExchangeRate
from payid.models import PayId
from requests.auth import HTTPBasicAuth 
import xmltodict
import re
# from django_otp.decorators import otp_required

# Your Account Sid and Auth Token from twilio.com/console
# DANGER! This is insecure. See http://twil.io/secure
account_sid = settings.TWILIO_ACCOUNT_SID
auth_token = settings.TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)

def password_validate(password):
    msg=[]
    if not re.findall('\d', password):    
        msg.append("The password must contain at least 1 digit, 0-9.")
    if not re.findall('[A-Z]', password):
        msg.append("The password must contain at least 1 uppercase letter, A-Z.")
    if not re.findall('[a-z]', password):
        msg.append("The password must contain at least 1 lowercase letter, a-z.")

    if not re.findall('[()[\]{}|\\`~!@#$%^&*_\-+=;:\'",<>./?]', password):
        msg.append("The password must contain at least 1 of these symbols: " +"()[]{}|\`~!@#$%^&*_-+=;:'\",<>./?")
    if len(password)<14:
        msg.append("Minimum length of password must be 14 characters")
    return msg        

class UpdateUserProfile(generics.UpdateAPIView):
    queryset=UserProfile.objects.all()
    serializer_class=UserProfileSerializer
    permission_classes=[IsAuthenticated,]

class TokenGenerator(PasswordResetTokenGenerator):
      pass

account_activation_token = TokenGenerator() 

class UserCreate(APIView):
    permission_classes = [AllowAny,]
    parser_classes = (MultiPartParser, FormParser,)
    def post(self, request, *args,**kwargs):
        serializer = UserSerializer(data=request.data)
        success = {}
        error = {}
        if serializer.is_valid():
            data=serializer.data
            email= data['email']
            email = email.lower()
            password=request.data['password']
            username=data['username']
            phone_number=data['phone_number']
            name=data['name']
            address=data['address']
            pincode=data['pincode']
            dob=data['dob']
            # validate password manually
            password_msgs=password_validate(password)
            if len(password_msgs)>0:
                return Response({"error":{"password": password_msgs},"success":False}, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info("dob is",dob)
            logger.info("dob type is",type(dob))

            occupation=data['occupation']
            id_document=request.data['id_document']
            logger.info("id_document",id_document)
            currency_id = data.get('currency_id',None)
            alpha2code = data.get('alpha2code',None)
            logger.info("alpha2code is ",alpha2code)
            logger.info("currency_id is ",currency_id)
            # country_code = data.get('country_code',None)
            # country_name = data.get('country_name',None)
            is_politically_exposed = data['is_politically_exposed']
            

            phone_number = phone_number.replace(" ", "")

            if currency_id is not None:
                currency_obj = Currency.objects.get(id=currency_id)
            else:
                currency_obj = None

            if alpha2code is not None:
                country_obj = Country.objects.get(alpha2code=alpha2code)
            else:
                country_obj = None                


            
            user= User.objects.create_user(email=email,password=password,username=username)


            user_profile = UserProfile.objects.create(user=user,phone_number=phone_number,
                    is_politically_exposed=is_politically_exposed,
                    currency_obj=currency_obj,nation=country_obj,name=name,address=address,pincode=pincode,
                    occupation=occupation,dob=dob,id_document=id_document)
            # Storing password
            track_pssword=UserOldPassword.objects.create(user=user,old_password=password)

            service = client.verify.services.create(friendly_name='STB Verify Service')
            
            service_sid = (service.sid)

            logger.info("service sid is",service_sid)
            user_profile.service_sid = service_sid
            user_profile.save()


            if alpha2code is not None:
                country_code = country_obj.dialing_code
            else:
                country_code = "+1"

            phone = str(country_code)+str(phone_number)


            app_hash = settings.SMS_APP_HASH
            try:
                sms = client.verify.services(service_sid).verifications.create(
                    to=phone, channel='sms',app_hash=app_hash)


            except Exception as e:
                try:
                    logger.info("error in sending otp is ",str(e))
                    user.delete()
                    return Response({"error":{"phone_number": [
                        "Invalid Phone Number"
                        ]},"success":success}, status=status.HTTP_400_BAD_REQUEST)
                except:
                    pass

            logger.info("otp sent for create user")
            thread1 = threading.Thread(target=create_ripple_wallet_and_bitcoin_addresss, args=(user,))
            thread2 = threading.Thread(target=send_activation_mail, args=(user,))
                     
            thread1.start()
            thread2.start()
           
        
           
            if user:               
                token = get_tokens_for_user(user=user)
                json_data = serializer.data

                json_data['user_id'] = user.id
                json_data['user_profile_id'] = user.id
                json_data['id_document'] = user_profile.id_document.url
                json_data['access'] = token['access']
                json_data['refresh'] = token['refresh']



                return Response({"success":json_data,"error":error}, status=status.HTTP_201_CREATED)
        errors = serializer.errors
        logger.info("error is ",errors)
        return Response({"error":serializer.errors,"success":success}, status=status.HTTP_400_BAD_REQUEST)


class DocumentTypes(APIView):
    permission_classes = [AllowAny,]

    def get(self,request):
        # user = request.user
        doc_types=[
            {'PP':'Passport'},
            {'DL':"Driver's Licence"},
            {'ID':'Government issued Identity Card'},
            {'UB':'Utility Bill'},
            {'RP':'Residence Permit'},
        ]
        return Response({"doc_types":doc_types},status=200)



class LoginView(APIView):
    permission_classes = [AllowAny,]
    def post(self,request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.user
            token = get_tokens_for_user(user=user)

            access = token['access']
            refresh = token['refresh']
            
            token = {'refresh': str(refresh), 'access': str(access)}  

            return Response(token,status=200)

        return Response({"detail":serializer.errors,"success":{}}, status=401)



class ResendOTPView(APIView):
    def get(self,request):
        user = request.user
        if user.phone_verfied is True:
            return Response({"msg":"not authorized"},status=401)

        

        user_profile = user.user_profile
        service = client.verify.services.create(friendly_name='STB Verify Service')
        
        service_sid = (service.sid)
        user_profile.service_sid = service_sid
        logger.info("service_sid uis",service_sid)
        user_profile.save()

        thread3 = threading.Thread(target=send_otp_to_user, args=(user,))
        thread3.start()             
        
        return Response({"msg":"Success"},status=200)

class VerifyOtp(APIView):
    def post(self, request, format=None):
        user = request.user
        email = user.email
        user_profile_obj = UserProfile.objects.get(user=user)
        phone_number = user_profile_obj.phone_number
        country_code = user_profile_obj.nation.dialing_code
        data = request.data
        otp_entered = str(data['otp'])

        phone_number = user.user_profile.phone_number

        logger.info("phone number is",phone_number)
        country_code = user.user_profile.nation.dialing_code

        logger.info("country code is",country_code)
        # verification = authy_api.phones.verification_check(phone_number,country_code
        #             , otp_entered)

        phone = str(country_code)+str(phone_number)
        service_sid = user_profile_obj.service_sid
        try:
            verification = client.verify.services(service_sid).verification_checks.create(
            to=phone, code=otp_entered)

        except Exception as e:
            logger.info("error is ",e)
            return Response({"msg":"OTP expired","otp_entered":otp_entered}, status=status.HTTP_400_BAD_REQUEST)
            # return Response({"msg":"Not Verified","otp_entered":otp_entered},status=400)
        if verification.status != "approved": 
            return Response({"msg":"Invalid OTP","otp_entered":otp_entered}, status=400)
        else:
            user.phone_verfied = True
            user.save()
            is_politically_exposed = user_profile_obj.is_politically_exposed
            if is_politically_exposed is True:
                pep_user_signed(user)


        return Response({"msg":"Verified","otp_entered":otp_entered},status=200)

        
class ChangePhoneNumber(APIView):
    def post(self, request, format=None):
        user = request.user
        serializer = ResetPhoneSerializer(data=request.data)
        
        if serializer.is_valid():
            logger.info("@132")
            user_profile_obj = UserProfile.objects.get(user=user)
            data = serializer.data
            logger.info("dats is",data)
            mobile_no = data['phone_number']
            mobile_no = str(mobile_no)
            logger.info("mobile_nummber is ",mobile_no)
            alpha2code = data['alpha2code']
            logger.info("alpha2code is ",alpha2code)

            if alpha2code is not None:
                country_obj = Country.objects.get(alpha2code=alpha2code)
            else:
                country_obj = Country.objects.get(alpha2code="CA")
    
            user_profile_obj.phone_number = mobile_no
            user_profile_obj.nation = country_obj

            service = client.verify.services.create(friendly_name='STB Verify Service')           
            service_sid = (service.sid)
            
            user_profile_obj.service_sid = service_sid            
            user_profile_obj.save()

            country_code = country_obj.dialing_code

            phone = str(country_code)+str(mobile_no)
            app_hash = settings.SMS_APP_HASH
            try:
                sms = client.verify.services(service_sid).verifications.create(
                    to=phone, channel='sms',app_hash=app_hash)



            except Exception as e:
                logger.info("error in sending otp is ",e)
                return Response({"msg":"Invalid Number"}, status=status.HTTP_400_BAD_REQUEST)

            thread = threading.Thread(target=send_otp_to_user, args=(user,))
            thread.start() 
            return Response({"msg":"Success"},status=200)

        if serializer.errors:
            error = {}
            errors = serializer.errors
            logger.info("error is ",errors)
            if errors.get('phone_number',None) is not None:
                error = errors['phone_number'][0]
            elif errors.get('alpha2code',None) is not None:
                error = errors['alpha2code'][0]

        return Response({"msg":error}, status=status.HTTP_400_BAD_REQUEST)



class VerificationStatus(APIView):
    def get(self, request, format=None):
        user = request.user

        is_email_verfied = user.email_verfied
        is_phone_verfied = user.phone_verfied
        return Response({"is_email_verified":is_email_verfied,"is_phone_verified":is_phone_verfied},status=200)
    
def test_email_send(request,email_address):
        try:
            test_email(email_address)
            return Response({"msg":"Please check your email for verfication"},status=200)
        except Exception as e:
            return Response({"msg":str(e)},status=400)

class ResendEmail(APIView):
    def get(self,request):
        user = request.user
        try:
            send_activation_mail(user)
            return Response({"msg":"Please check your email for verfication"},status=200)
        except Exception as e:
            return Response({"msg":str(e)},status=400)


def ValidateEmail(request):   

    uidb64 = request.GET.get('uid')
    token = request.GET.get('token')
    logger.info("udi64 is ",uidb64)
    logger.info("token is ",token)

    # logo_obj = Logo.objects.filter(active=True).first()
    current_url = settings.CURRENT_API_URL
    context = {
          #try to use python reveerse method for url        
            'image_url':"image_url"
            # 'image_url':current_url + str(logo_obj.image.url)
        }
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        new_user = User.objects.get(id=uid)
        
        if new_user is not None and account_activation_token.check_token(new_user, token):
            new_user.is_active = True
            new_user.email_verfied = True
            new_user.save()
            try:
                thread1 = threading.Thread(target=send_mail_for_register, args=(new_user,))
                thread1.start()
            except Exception as e:
                logger.info('error in registration email',str(e))
            return render(request,'email/thankyou.html',context)    # redirecting by using name
        else:
            return render(request,'email/activation_link_invalid.html',context)
    except User.DoesNotExist:
        return render(request,'email/user_not_found.html',context)       
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        new_user = None
        return render(request,'email/activation_link_invalid.html',context)
 


class ChangeEmail(APIView):
    def post(self, request, format='json'):
        data= request.data
        user = request.user
        serializer = ResetEmailSerializer(data=request.data)
        
        if serializer.is_valid():
            user_profile_obj = UserProfile.objects.get(user=user)
            data = request.data
            email = data['email']
            email = email.lower()
            user = request.user
            user.email = email
            user.save()
            thread = threading.Thread(target=send_activation_mail, args=(user,))
            thread.start()
            return Response({"msg":"Success"},status=200)
        return Response({"msg":(serializer.errors)['email'][0]}, status=status.HTTP_400_BAD_REQUEST)



class ProfileInfo(APIView):
    def get(self, request, format='json'):
        user = request.user
        username = user.username
        email = user.email
        user_profile_obj = UserProfile.objects.get(user=user)
        payid_obj = PayId.objects.get(user_profile = user_profile_obj)
        payid = payid_obj.get_uri()
        logger.info("payid is",payid)

        phone = user_profile_obj.phone_number
        currency_code = user_profile_obj.currency_obj.code
        country_name = user_profile_obj.nation.name
        name = user_profile_obj.name
        address = user_profile_obj.address
        pincode = user_profile_obj.pincode
        dob = user_profile_obj.dob
        occupation = user_profile_obj.occupation
        is_kyc_verfied = user_profile_obj.is_kyc_verfied
        id_document = user_profile_obj.id_document
        logger.info("type is ",type(id_document))
        logger.info("id_document is ",id_document)
        logger.info("name is ",id_document.name)
        if id_document.name!=u'':
            logger.info("length of name is ",len(id_document.name))
            id_document = id_document.url
        else:
            id_document = None
        # if dob is not None: 
        #     dob = dob.strftime("%Y-%m-%d")
        logger.info("id_document us",id_document)

        to_send = {
            'email':email,
            'phone':phone,
            'username':username,
            'country':country_name,
            'currency_code':currency_code,
            'name':name,
            'address':address,
            'pincode':pincode,
            'occupation':occupation,
            'dob':dob,
            'id_document':id_document,
            'payid':payid,
            'is_kyc_verfied':is_kyc_verfied,
            'user_profile_id':user_profile_obj.id

        }
        

        return Response({"msg":to_send}, 200)


class GetCountryDetails(APIView):
    permission_classes = [AllowAny,]
    def get(self,request,*args,**kwargs):
        to_send = Country.objects.all().values()
        return Response(to_send,status=200)


class GetCurrencyCode(APIView):
    permission_classes = [AllowAny,]
    def get(self,request,*args,**kwargs):
        to_send = get_currency_codes()
        to_send = Currency.objects.all().values('id','name','code')
        return Response(to_send,status=200)


from authy.api import AuthyApiClient
from accounts.models import *
authy_api = AuthyApiClient(settings.ACCOUNT_SECURITY_API_KEY)

def set_authy_id(request):
    user_profile_list = UserProfile.objects.all()

    for user_profile in user_profile_list:
        phone_number = user_profile.phone_number
        email = user_profile.user.email
        country_code = user_profile.nation.dialing_code
        if country_code is not  None:
            try: 
                authy_user = authy_api.users.create(email,phone_number,country_code)
            except  Exception as e:
                logger.info("error is ",e)
                continue
            authy_id = authy_user.id
            logger.info("authy id is ",authy_id)
            user = user_profile.user
            user.authy_id = authy_id
            user.save()

    
    
    return HttpResponse("authyid")



def set_currency(request):#ONLY NEEDED FOR INITIALISATION
    currency_list = get_currency_codes()
    for currency in currency_list:
        logger.info("currency code is",currency['id'])

        try:
            btc_to_currency = get_btc_to_currency(currency['id'])
        except Exception as e:
            logger.info("error is e",e)
            continue    
        logger.info("btc_to_currency is",btc_to_currency)
        try:
            currency_obj = Currency.objects.create(name=currency['name'],
            code=currency['id'],btc_to_currency=btc_to_currency)
        except Exception as e:
            logger.info("error is e",e)
            continue
    return HttpResponse("done")




def set_countries(request):
    country_list = get_all_country_details()

    for country in country_list:
        name = country['country_name']
        dialing_code = country['calling_code']
        dialing_code = "+" + str(dialing_code)
        flag_url = country['flag']
        default_currency_code = country['default_currency_code']
        alpha2Code = country['alpha2Code']


        try:
            currency_obj = Currency.objects.get(code=default_currency_code)
        except Exception as e: 
            currency_obj = Currency.objects.get(code="CAD")

        country_obj = Country.objects.create(name=name,dialing_code=dialing_code,
        flag_url=flag_url,default_currency=currency_obj,alpha2code=alpha2Code)
        
        logger.info("country name is",country_obj.name)
    return HttpResponse("done")

def set_historical_price(request): #FOR CALLING THRU CRON JOB
    currencies = ['CAD']
    app_id = AppConfiguration.objects.filter(active=True).first().coindesk_api_key
    today = timezone.now().today()
    start_date =  today-timedelta(days=8)
    today = today.strftime("%Y-%m-%d")     
    start_date =  start_date.strftime("%Y-%m-%d") 
    usd_request_url = "https://api.coindesk.com/v1/bpi/historical/close.json"#?start="+start_date+"&end="+today
    response = requests.get(usd_request_url)
    json_response = response.json()

    current_rate = "https://api.coindesk.com/v1/bpi/currentprice.json"
    resp = requests.get(current_rate)
    js_res = resp.json()
    bpi = json_response['bpi']
    bpi[today]=js_res['bpi']['USD']['rate_float']

    for currency in currencies:
        for date,rate in bpi.items():
            logger.info(datetime.combine(datetime.strptime(date,"%Y-%m-%d"), datetime.min.time()))
            if ExchangeRate.objects.filter(currency__code__iexact=currency,date_time__range = (datetime.combine(datetime.strptime(date,"%Y-%m-%d"), datetime.min.time()),datetime.combine(datetime.strptime(date,"%Y-%m-%d"), datetime.max.time()))).exists():
                logger.info('Exists')
                continue

            logger.info("date is",date)
            exchange_url = "https://openexchangerates.org/api/historical/"+str(date)+".json?app_id="+app_id
            response = requests.get(exchange_url)
            exchange_response = response.json()
            rates = exchange_response['rates']    


            # for code,value in rates.items():
            try:
                # logger.info("Trying for ",str(code))
                currency_obj = Currency.objects.get(code=currency)
                btc_to_currency = rate * rates[currency]
                logger.info("btc_to_currency is ",btc_to_currency)
                logger.info("currency is",currency,str(date))
                dt = datetime.combine(datetime.strptime(date,"%Y-%m-%d"), datetime.max.time())
                logger.info(dt)
                historical_price_obj = ExchangeRate.objects.create(rate=btc_to_currency,date_time = dt,currency=  currency_obj  )            
            except Exception as e:
                logger.info(str(e))
                pass

    return HttpResponse("done"+str(today))


class RegisterDevice(APIView):

    def post(self, request, format=None):
        data = request.data

        user = request.user
        device_type = data['device_type'] 
        token = data['token'] 

        logger.info("device_type is",device_type)
        logger.info("token is",token)
        if device_type=='android' or device_type=='ios' :
            try:    
                fcm_device = GCMDevice.objects.get(registration_id=token)

                #if new user register with same device update the device with new user   
                if fcm_device.user != user:
                    fcm_device.user = user 
                    
                    fcm_device.save()           
            except GCMDevice.DoesNotExist:

                '''Register the device here '''
                fcm_device = GCMDevice.objects.create(registration_id=token, cloud_message_type="FCM", user=user)
 
            return Response({"msg":"ok"},status=200)

        # if device_type=="ios":
        #     try:    
        #         ios_device = APNSDevice.objects.get(registration_id=token)

        #         #if new user register with same device update the device with new user   
        #         if ios_device.user != user:
        #             ios_device.user = user 
        #             ios_device.save()           
        #     except APNSDevice.DoesNotExist:
        #         logger.info("user @603 is",user)
        #         '''Register the device here '''
        #         ios_device = APNSDevice.objects.create(registration_id=token, user=user)
        #     return Response({"msg":"ok"},status=200)


        return Response({"msg":"ok"},status=200)



# def latest_ram(request, *args, **kwargs):

#     return RAM.objects.latest("modified_date").modified_date

# @method_decorator(cache_control(public=True, max_age=2), name='dispatch')
# class GetHistoricalPrice(ReadOnlyModelViewSet):
#     permission_classes = [AllowAny,]
#     search_fields = ['manufacturer','model']
#     filter_backends = (filters.SearchFilter,)
#     # @condition(last_modified_func=latest_ram)
#     def get_queryset(self):


class GetHistoricalPrice(APIView):
    # permission_classes = [AllowAny,]
    def get(self, request, *args,**kwargs):
        user = request.user
        now = timezone.now()
        user_profile_obj = UserProfile.objects.get(user=user)
        currency = user_profile_obj.currency_obj
        # currency = Currency.objects.get(code="INR")
        price_list = ExchangeRate.objects.filter(
        currency=currency,date_time__lte=now,date_time__gte=now-timedelta(days=7))
        to_send = {}
        for price_obj in price_list:
            to_send[price_obj.date_time.strftime("%Y-%m-%d")] = price_obj.rate  
        logger.info(to_send)
        return Response({"price_list":to_send},status=200)


class GetVersionStatus(APIView):
    permission_classes = [AllowAny,]
    def get(self, request, *args,**kwargs):
        version_list = Version.objects.all().values('name','is_active')
        logger.info("version_list is",version_list)
        return Response({"version_list":version_list},status=200)



def delete_historical_price(request):
    price_list = HistoricalPrice.objects.all()

    for price in price_list:
        price.delete()

    return HttpResponse("ok")


def set_canada(request):
    user_profile_list = UserProfile.objects.all()
    canada = Country.objects.get(alpha2code="CA")
    for user_profile in user_profile_list:
        user_profile.nation = canada
        user_profile.save()

    return HttpResponse("ok")


def delete_currency_nation(request):
    logger.info("came in delete_currency_nation")
    user_profile_list = UserProfile.objects.all()
    for user_profile in user_profile_list:
        logger.info("user_profile is",user_profile.user.username)
        # user_profile.nation = canada
        
        user_profile.delete()

    nation_list = Country.object.all()

    for country  in nation_list:
        logger.info("county is",country.name)
        country.delete()  

    
    currency_list = Currency.objects.all()

    for currency_obj in currency_list:
        logger.info("currency_obj is",currency_obj.name)
        currency_obj.delete()



    return HttpResponse("delete")  

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def dv_callback(request):
    logger.info("came in dv_callback")

    logger.info("request is",request)
    body = request.body
    logger.info("body is",body)
    return HttpResponse("dv_callback")  





@receiver(pre_delete, sender=User)
def delete_user_account(sender, instance: User, **kwarg):
    try:
        logger.info('user instance=',instance)
        stb_wallet=RippleWallet.objects.get(user=instance)
        logger.info('deleting wallet=',stb_wallet)
        # Delete ripple account of deleting user
        thread1 = threading.Thread(target=disable_account, args=(stb_wallet.account_id,stb_wallet.master_seed))
        thread1.start()
        logger.info('ripple account deleted')
        # check_delete_ripple_addrs=disable_account(stb_wallet.account_id,stb_wallet.master_seed)
    except Exception as e:
        logger.info('error=',str(e))
        logger.info('something is wrong to delete user with xrpl')

# pre_delete.connect(delete_user_account,sender=User)

def send_transaction_mail(request):
    to_mail='sushantamandal91@gmail.com'
    html_addr='email/register_email.html'
    text_address = 'email/common_text.txt'
    # subject="Thank you for the transaction"
    subject="Welcome to SpendtheBits"

    context={
        "user":'sushanta',
        "amount":100
        # "reference":transaction_obj.reference_number
    }
    send_mail(to_mail,subject,context,html_addr,text_address)
    return HttpResponse('done')
