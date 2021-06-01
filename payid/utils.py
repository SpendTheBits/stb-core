from .models import *
from django.conf import settings
import requests



def get_payid_object(payid):


    logger.info("payid is",payid)

    if payid is None:
        return None
        
    if '$' not in payid:
        return None


    host = (payid.split('$'))[1]
    name = (payid.split('$'))[0]
    
    host_to_compare = settings.PAYID_URI_DOMAIN
    logger.info("host is",host)
    logger.info("name is",name)
    logger.info("host_to_compare is",host_to_compare)

    if host!=host_to_compare:
        return None
        
    try:
        payid_obj = PayId.objects.get(name__iexact=name)
    except Exception as e:
        logger.info("error in payid us",e)
        return None


    return payid_obj