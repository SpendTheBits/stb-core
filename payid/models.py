from django.db import models
from django.conf import settings

from accounts.models import UserProfile


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

def get_payid_uri( name ):
    return ''.join((name.lower(), '$', settings.PAYID_URI_DOMAIN))

class PayId(BaseModel):
    # For payid entities managed on this server
    name = models.CharField(max_length=80)
    memo = models.CharField(max_length=120, default="None")
    user_profile = models.ForeignKey(UserProfile,on_delete=models.CASCADE)

    def get_uri(self):
        j =  get_payid_uri( self.name )
        logger.info("j is ",str(j))
        return str(j)

    def get_crypto(self, hide_if_not_show=True):
        queryset = CryptoAddress.objects.filter(entity=self,show=True)

        return queryset


    def __str__(self):
        return self.name

#TODO : This model should be removed acc to me ADitya 27-11-20

class CryptoAddress(BaseModel):

    paymentNetwork = models.CharField(max_length = 8)
    environment = models.CharField(max_length = 12) # mainnet, testnet, etc.
    
    show = models.BooleanField(default=True)
    entity = models.ForeignKey(PayId, on_delete=models.CASCADE)

    address = models.CharField(max_length = 128) 


