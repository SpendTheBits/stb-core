from django.db import models
from django.conf import settings
from accounts.models import User
# Create your models here.



class KycAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ('-created_date',)



class KycApplication(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
        related_name='kyc_applications',blank=True,null=True)
    application_id = models.CharField(max_length=400)
    status = models.CharField(max_length=50)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.application_id

class KycApplicationErrorAndSuggest(models.Model):
    application=models.ForeignKey(KycApplication,on_delete=models.CASCADE)
    error_message = models.CharField(max_length=300)
    action_suggested = models.CharField(max_length=300)

    def __str__(self):
        return str(self.application)