from django.shortcuts import render
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *
from .models import *
from accounts.utils import *
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny
import magic
from django.views.decorators.csrf import csrf_exempt
# Create your views here.
import urllib.request
import ssl
import json
import base64
import datetime
from datetime import timedelta
from django.utils import timezone
import requests
from requests.auth import HTTPBasicAuth
from rest_framework.parsers import FormParser, MultiPartParser

def get_mimetype(document):
    with open(document, "rb") as image_file:
        image_str = base64.b64encode(image_file.read())
        image_str = str(image_str,'utf-8')
        try:
            output=magic.from_file(document,mime=True)
            output_image_str = str(output)+";base64,"+ image_str
            return output_image_str 
        except Exception as e:
            return None
        

class UpdateKyc(APIView):
    success = {}
    
    parser_classes = (MultiPartParser, FormParser,)

    def post(self, request, *args,**kwargs):
        # logger.info("Data is:",request.data)
        serializer = KycSerializer(data=request.data,context={'request': request})
        errors = {}
        error=''
        if serializer.is_valid():        
            data=request.data
            user= request.user
            logger.info('user=',user,)
            user_profile_obj = user.user_profile
            front_part_of_document = data.get('front_part_of_document',None)
            back_part_of_document = data.get('back_part_of_document',None)
            selfie = data.get('selfie',None)
            document_type = data.get('document_type',None)

            if document_type is not None:
                user_profile_obj.document_type = document_type
            if selfie is not None:
                user_profile_obj.selfie = selfie        

            if front_part_of_document is not None:
                user_profile_obj.front_part_of_document = front_part_of_document   
            if back_part_of_document is not None:
                user_profile_obj.back_part_of_document = back_part_of_document   

            user_profile_obj.save()
            
            return Response({"success":{"msg":"ok"},"error":errors}, status=status.HTTP_201_CREATED)


        if serializer.errors:
            logger.info(serializer.errors)
            errors = serializer.errors
            logger.info("errors in stb to stb is",errors)
            if errors.get('non_field_errors',None) is not None:
                error = {"message":errors['non_field_errors'][0]}

        return Response({"error":error,"success":{}}, status=status.HTTP_400_BAD_REQUEST)


class StartKyc(APIView):

    def get(self, request, *args,**kwargs):
        error = ''
        user= request.user
        logger.info('user=',user)
        user_profile_obj = user.user_profile
        name = user_profile_obj.name
        dob = user_profile_obj.dob
        
        is_kyc_verfied = user_profile_obj.is_kyc_verfied
        document_type = user_profile_obj.document_type
        
        front_part_str=''
        
        error_message = ''
        action_suggested = ''
        errors=[]
        action_suggests=[]
        base_dir = settings.BASE_DIR
        try:
            back_part_of_document = base_dir + user_profile_obj.back_part_of_document.url
            output_back_part=get_mimetype(back_part_of_document)    
            back_image_str=output_back_part
            front_part_of_document = base_dir + user_profile_obj.front_part_of_document.url  
            output_front_part=get_mimetype(front_part_of_document)
            front_part_str=output_front_part

            selfie=base_dir+user_profile_obj.selfie.url
            output_face_part=get_mimetype(selfie)
            face_image_str=output_face_part
        except Exception as e:
            logger.info(str(e))
            msg="Your KYC application is rejected due to invalid documents"
            send_notification(user,msg)
            res={
                "is_kyc_verfied":user_profile_obj.is_kyc_verfied,
                'selfie':'',
                'front_part_of_document':'',
                'back_part_of_document':'',
                'document_type':'',
                'status':"Not Done",
                "action_suggested":["Please upload your valid documents"],
                "error_message":str(e),
            }
            return Response({"success":res})
        payload = {
            'man':user.username,
            'docCountry':str(user_profile_obj.nation.alpha2code),
            "backsideImageData":back_image_str,
            'faceImages':[face_image_str],
            "docType":document_type,
            "dob":dob,
            "scanData":front_part_str,
            "tea":user.email,
            "pm":user_profile_obj.phone_number,
            "phn":user_profile_obj.phone_number,
            "nationality":str(user_profile_obj.nation.alpha2code),
            "bco":str(user_profile_obj.nation.alpha2code),
            "bz":user_profile_obj.pincode,
            "bfn":name.split(" ")[0],
            "bln":name.split(" ")[-1]
            
        }
        querystring = {"graphScoreResponse":"false"}

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        # HTTPBasicAuth
        username = settings.KYC_USERNAME #'spendthebits'
        password = settings.KYC_PASSWORD

        url = settings.KYC_URL

        response = requests.request("POST", url, json=payload, headers=headers, params=querystring,
                auth = HTTPBasicAuth(username,password) ,)
        response = response.json()
        logger.info('response=',response)
        # try:
        kyc_application,created = KycApplication.objects.get_or_create(user=user)

        #Delete existing reasons and suggestions
        try:
            kyc_err_suggest=KycApplicationErrorAndSuggest.objects.filter(application=kyc_application).delete()
        except:
            pass


        kyc_attempt = KycAttempt.objects.create(user=user)
        logger.info('creating a new kyc',response)
        state = response['state']
        mtid = response['mtid']   
        kyc_application.application_id = mtid
        if state=='A':
            user_profile_obj.is_kyc_verfied=True
            kyc_application.status = 'Accepted'
        logger.info("HERE ADITYA2")
        if state=='D':
            kyc_application.status = 'Rejected'
            for data in response['ednaScoreCard']['etr']:
                try:
                    if data['fired']:
                        # errors+=data['details']
                        kyc_err_suggest=KycApplicationErrorAndSuggest.objects.create(application=kyc_application,error_message=data['details'],action_suggested="")
                        errors.append(data['details'])
                        # action_suggests.append(data.action_suggested)
                except:
                    pass

        logger.info("HERE ADITYA1")
        if state=='R':
            kyc_application.status = 'Under Review'
        user_profile_obj.save()
        kyc_application.save()
        logger.info("HERE ADITYA")

                
        front_part_of_document = str(user_profile_obj.front_part_of_document.url)
        back_part_of_document = str(user_profile_obj.back_part_of_document.url)
        selfie = str(user_profile_obj.selfie.url)
        is_kyc_verfied = user_profile_obj.is_kyc_verfied
        document_type = user_profile_obj.document_type

        logger.info("back_part_of_document is",back_part_of_document)
        
        to_send ={
        'is_kyc_verfied':is_kyc_verfied,
        'selfie':str(selfie),
        'front_part_of_document':front_part_of_document,
        'back_part_of_document':back_part_of_document,
        'document_type':document_type,
        'status':kyc_application.status,
        'error_message':errors,
        "action_suggested":[]
        
        }
        if is_kyc_verfied:
            msg="Your KYC application is approved"
            send_notification(user,msg)

        return Response({"success":to_send}, status=200)
    
class GetKycStatus(APIView):

    def get(self, request, *args,**kwargs):
        logger.info("came in GetTransactionBreakup ")
        success = {}
        errors = []
        action_suggests=[]
        selfie=''
        front_part_of_document=''
        back_part_of_document=''
        user= request.user
        user_profile_obj = user.user_profile
        is_kyc_verfied = user_profile_obj.is_kyc_verfied
        error_message=''
        # logger.info('check file',user_profile_obj.back_part_of_document)
        try:
            kyc_application = KycApplication.objects.get(user=user)
            status = kyc_application.status
            # error_message = kyc_application.error_message
            # action_suggested = kyc_application.action_suggested
            logger.info('existing kyc')
            # res_err_sggst=[]
            
            if status=="Rejected":
                error_and_suggest=KycApplicationErrorAndSuggest.objects.filter(application=kyc_application)

                for data in error_and_suggest:
                    errors.append(data.error_message)
                    action_suggests.append(data.action_suggested)
                    # d={
                    #     "error":data.error_message,
                    #     "suggest":data.action_suggested
                    # }
                    # res_err_sggst.append(d)
 
        except Exception as e :
            logger.info('exception')
            status='Not Done'
            errors.append(str(e))
        try:
            front_part_of_document = str(user_profile_obj.front_part_of_document.url) 
        except Exception as e:
            errors.append(str(e))
            action_suggests.append("Upload front part of document")
        try:
            back_part_of_document = str(user_profile_obj.back_part_of_document.url)  
        except Exception as e:
            errors.append(str(e))
            action_suggests.append("Upload back part of document")


        try:
            selfie = str(user_profile_obj.selfie.url)  
        except Exception as e:
            errors.append(str(e))
            action_suggests.append("Upload selfie")


        res={
            
            "is_kyc_verfied":is_kyc_verfied,
            # "error_suggest":res_err_sggst,
            'selfie':selfie,
            'front_part_of_document':front_part_of_document,
            'back_part_of_document':back_part_of_document,
            # 'name':user_profile_obj.name,
            # 'dob':str(user_profile_obj.dob),
            'document_type':user_profile_obj.document_type if user_profile_obj.document_type is not None else '',
            "status":status,
            # "action_suggested":action_suggested
            "error_message":errors,
            "action_suggested":action_suggests
        }
        return Response({"success":res}, status=200)

@csrf_exempt
def handle_kyc_response(request):
    logger.info("came in handle_kyc_response")

    
    body = request.body.decode("utf-8") 
    logger.info("body is",body)


    body = json.loads(body)


    mtid = body['mtid']
    kyc_application = KycApplication.objects.get(application_id=mtid)
    kyc_err_suggest=KycApplicationErrorAndSuggest.objects.filter(application=kyc_application).delete()

    user = kyc_application.user
    user_profile_obj = user.user_profile

    errors=""
    suggest=""
    state = body['state']
    if state=='A':
        user_profile_obj.is_kyc_verfied=True
        user_profile_obj.save()
        kyc_application.status = 'Accepted'
        # kyc_application.save()
        # kyc_err_suggest=KycApplicationErrorAndSuggest.objects.filter(application=kyc_application).delete()

    if state=='D':
        kyc_application.status = 'Rejected'
        
        for data in body['ednaScoreCard']['etr']:
            if data['test']=='dv:0':
                try:
                    if data['fired']:
                        kyc_err_suggest=KycApplicationErrorAndSuggest.objects.create(
                            application=kyc_application,
                            error_message=data['details'],
                            action_suggested="Please give correct document"
                        )
                        errors+=data['details']+","
                except:
                    pass
            if data['test']=='dv:1':
                try:
                    if data['fired']:
                        err_msg=''
                        if type(data['details'])==str:
                            err_msg=data['details']
                        elif type(data['details'])==list:
                            err_msg=data['details'][0]

                        kyc_err_suggest=KycApplicationErrorAndSuggest.objects.create(
                            application=kyc_application,
                            error_message=err_msg,
                            action_suggested="Please give correct document"
                        )
                        errors+=data['details']+","
                        suggest+="Please give correct document,"
                except:
                    pass
            if data['test']=='dv:2':
                try:
                    if data['fired']:
                        err_msg=''
                        if type(data['details'])==str:
                            err_msg=data['details']
                        elif type(data['details'])==list:
                            err_msg=data['details'][0]
                            
                        kyc_err_suggest=KycApplicationErrorAndSuggest.objects.create(
                            application=kyc_application,
                            error_message=err_msg,
                            action_suggested="Select correct document type"
                        )
                        errors+=data['details']+","
                        suggest+="Select correct document type,"
                except:
                    pass
            
            if data['test']=='dv:3':
                try:
                    if data['fired']:
                        err_msg=''
                        if type(data['details'])==str:
                            err_msg=data['details']
                        elif type(data['details'])==list:
                            err_msg=data['details'][0]
                        kyc_err_suggest=KycApplicationErrorAndSuggest.objects.create(
                            application=kyc_application,
                            error_message=err_msg,
                            action_suggested="Submit other id proof"
                        )
                        errors+=data['details']+","
                        suggest+="Submit other id proof,"
                except:
                    pass

            if data['test']=='dv:9':
                try:
                    if data['fired']:
                        kyc_err_suggest=KycApplicationErrorAndSuggest.objects.create(
                            application=kyc_application,
                            error_message=data['details'],
                            action_suggested="Give correct Date of Birth"
                        )
                        errors+=data['details']+","
                except:
                    pass
        logger.info('total error=',errors)
    kyc_application.save()

    return HttpResponse("handle_kyc_response done")  
