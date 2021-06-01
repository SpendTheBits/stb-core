from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
import threading
import requests
import decimal

from django.utils import timezone
from datetime import timedelta,datetime
from ripple_wallet.models import BaseModel,AppConfiguration,Currency,ExchangeRate

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""
    use_in_migrations = True

    def _create_user(self, email,username, password, **extra_fields):
        #this is a private method and should not be used anywhere by anyone
        """Create and save a User with the given email and password."""
        is_staff = extra_fields.get('is_staff')
        if is_staff is True:
            user = self.model(username=username, **extra_fields)
        else:            
            if not email:
                raise ValueError('The given email must be set')
            email = self.normalize_email(email)
            user = self.model(email=email,username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email,username, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email,username, password, **extra_fields)

    def create_superuser(self,username,password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(None,username,password, **extra_fields)


class User(AbstractUser):

    email = models.EmailField()
    phone_verfied = models.BooleanField(default=False)
    email_verfied = models.BooleanField(default=False)
    token = models.CharField(max_length=10,null=True,blank=True)
    is_freezed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    user_type=models.CharField(max_length=20,null=True,blank=True,choices=(("superadmin","Super Admin"),("admin","Admin"),("support","Support staff"),("aml","AML")))
   

    objects = UserManager()

    def __str__(self):
        return str(self.username)

    class Meta:
        verbose_name='User'
        verbose_name_plural='Users'




class Country(models.Model):
    name = models.CharField(max_length=1000,unique=True)
    dialing_code = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    flag_url = models.CharField(max_length=1000,null=True,blank=True)
    alpha2code = models.CharField(max_length=100,null=True,blank=True)

    class Meta:
        verbose_name_plural = 'Countries'
        ordering = ('name',)
    
    def __str__(self):
        return str(self.name)


class UserProfile(models.Model):
    document_choices = [
    ('PP','Passport'),
    ('DL',"Driver's Licence"),
    ('ID','Government issued Identity Card'),
    ('UB','Utility Bill'),
    ('RP','Residence Permit'),
    ]
        
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
        related_name='user_profile',blank=True,null=True)
    image = models.FileField(upload_to='image/users/', null=True,blank=True, verbose_name="image")
    phone_number = models.CharField(max_length=17,blank=True,null=True)
    currency_obj = models.ForeignKey(Currency,on_delete=models.SET_NULL,null=True,blank=True,verbose_name="currency")
    is_politically_exposed = models.BooleanField(default=False)
    nation = models.ForeignKey(Country,on_delete=models.SET_NULL,null=True,blank=True)
    on_receive = models.BooleanField(default=False) #TODO Give Description
    on_funding = models.BooleanField(default=False)#TODO Give Description
    service_sid = models.CharField(max_length=300,null=True,blank=True) #TODO Give Description
    name = models.CharField(max_length=300,null=True,blank=True)
    address = models.CharField(max_length=1500,null=True,blank=True)
    pincode = models.CharField(max_length=300,null=True,blank=True)
    dob = models.CharField(max_length=300,null=True,blank=True)
    occupation = models.CharField(max_length=1000,null=True,blank=True)
    id_document = models.FileField(null=True,blank=True)
    is_kyc_verfied = models.BooleanField(default=False)
    front_part_of_document = models.FileField(null=True,blank=True)
    back_part_of_document = models.FileField(null=True,blank=True)
    selfie = models.FileField(null=True,blank=True)
    document_type = models.CharField(max_length=100,null=True,blank=True,choices = document_choices)


    def __str__(self):
        return str(self.user)

class Version(models.Model):
    release_date = models.DateField()
    name = models.CharField(max_length=20)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class DerogatoryWords(models.Model):
    word = models.CharField(max_length=500)

    def __str__(self):
        return self.word