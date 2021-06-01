from django.contrib.auth import get_user_model  # gets the user_model django  default or your own custom
# from django.contrib.auth.backends import ModelBackend
# from django.db.models import Q
import time
from .models import User
import logging
logger = logging.getLogger(__name__)
# Class to permit the athentication using email or username
class EmailOrUsernameModelBackend(object):

    def authenticate(self, request, username=None, password=None):
        logger.info('username=',username)
        
        
        kwargs = {'username': username}
        try:
            # user = get_user_model().objects.get(**kwargs)
            user = User.objects.get(username=username)
            logger.info('user email=',user.email)
            
            if user.check_password(password):
                # logger.info('password verified')
                time.sleep(1)
                if not user.is_staff:
                    return user
                if '@spendthebits.com' in str(user.email).lower():
                    logger.info('email verified')
                    return user
            
            return None
                # return user
            
        except User.DoesNotExist:
            logger.info('call error')
            return None

    def get_user(self, username):
        try:
            return get_user_model().objects.get(pk=username)
        except get_user_model().DoesNotExist:
            return None
