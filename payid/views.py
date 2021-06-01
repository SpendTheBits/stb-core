from django.shortcuts import render
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.serializers import *
from accounts.models import *
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny
from django.conf import settings

from datetime import timedelta
from django.utils import timezone
import requests
from twilio.rest import Client
from rest_framework.parsers import FormParser, MultiPartParser



from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from .models import *


from rest_framework.negotiation import BaseContentNegotiation

class IgnoreClientContentNegotiation(BaseContentNegotiation):
    def select_parser(self, request, parsers):
        """
        Select the first parser in the `.parser_classes` list.
        """
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix):
        """
        Select the first renderer in the `.renderer_classes` list.
        """
        return (renderers[0], renderers[0].media_type)

def fetch_account(payid_obj):

    result = { "payId": payid_obj.get_uri(), "memo": payid_obj.memo, "addresses": [] }
    for addr in payid_obj.get_crypto():
        result['addresses'].append( {
            "paymentNetwork": addr.paymentNetwork,
            "environment": addr.environment,
            "addressDetailsType": "CryptoAddressDetails",
            "addressDetails": {
                "address": addr.address,
                }
            })

    return (result)


def fetch_address(payid_obj,network,environment):
    logger.info("network is",network)
    logger.info("environment is",environment)
    crypto_obj = CryptoAddress.objects.get(entity=payid_obj,paymentNetwork__iexact=network
    ,environment__iexact=environment)

    address = {
            "paymentNetwork": crypto_obj.paymentNetwork,
            "environment": crypto_obj.environment,
            "addressDetailsType": "CryptoAddressDetails",
            "addressDetails": {
                "address": crypto_obj.address,
                }
            }
    result = { "payId": payid_obj.get_uri(), "memo": payid_obj.memo, "addresses": [address,] }
    return (result)

class ParsePayid(APIView):
    permission_classes = [AllowAny,]
    content_negotiation_class = IgnoreClientContentNegotiation
    def get(self,request,name,*args,**kwargs):
        try:
            version_header = request.headers["PayID-Version"]
        except KeyError:
            return Response("Missing PayId Version", status=401)
        if version_header != "1.0":
            return Response("Unsupported PayID Version {}".format(version_header), status=401)


        try:
            accept_header = request.headers["Accept"]
        except KeyError:
            return Response("Missing Accept in Header", status=401)

        logger.info("accept_header is ",accept_header)
        try:
            payid_obj = PayId.objects.get(name__iexact=name)
        except Exception as e:
            return Response("No user Found", status=404) 
        

        if accept_header == "application/payid+json":
            result = fetch_account(payid_obj)
            return Response(result)
        elif accept_header == "application/xrpl-testnet+json":
            result = fetch_address(payid_obj,"XRPL","testnet")
            return Response(result)
        elif accept_header == "application/xrpl-mainnet+json":
            result = fetch_address(payid_obj,"XRPL","mainnet")
            return Response(result)
        elif accept_header == "application/btc-mainnet+json":
            result = fetch_address(payid_obj,"BTC","mainnet")
            return Response(result)           
        else:
            return Response("No Address Found for this network", status=404) 