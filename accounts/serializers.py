from rest_framework import exceptions,serializers
from rest_framework.validators import UniqueValidator,UniqueTogetherValidator
from accounts.models import *
import django.contrib.auth.password_validation as validators
from xrpl_wallet.models import Currency
from django.contrib.auth import authenticate


from datetime import datetime


class UserSerializer(serializers.Serializer):
    email = serializers.EmailField(
            required=True,
            validators=[UniqueValidator(queryset=User.objects.filter(email_verfied=True),message = 'email already exists')]
            
            )
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(max_length=150,required=True,
                validators=[UniqueValidator(queryset=User.objects.all(),message = 'username already exists')]
                 )
    phone_number = serializers.CharField(max_length=15,required=True)
    alpha2code = serializers.CharField(max_length=10)
    name = serializers.CharField(max_length=300)
    address = serializers.CharField(max_length=1500)
    pincode = serializers.CharField(max_length=300)
    dob = serializers.CharField(max_length=300)
    occupation = serializers.CharField(max_length=300)
    currency_id = serializers.IntegerField(required=False)
    is_politically_exposed = serializers.BooleanField()
    id_document = serializers.FileField()


    def validate(self, data):
        password = data.get('password')
        alpha2code = data.get('alpha2code')
       
        currency_id = data.get('currency_id')
        
        phone_number = data.get('phone_number')
        username = data.get('username')
        dob = data.get('dob')
        username = username.lower()


        
        id_list = Currency.objects.all().values_list('id',flat=True)
        alpha2_list = Country.objects.all().values_list('alpha2code',flat=True)
        
        check_list = "abcdefghijklmnopqrstuvwxyz@.+-_0123456789"

        errors = dict()
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d")
        # dob = "-".join((dob.split("-"))[::-1])
        current_year = int(now.strftime("%Y"))
        current_month = (now.strftime("%m"))
        current_day = (now.strftime("%d"))
        logger.info("current_year ",current_year)
        year_to_match = current_year - 16
        year_to_match = str(year_to_match)


        last_date_to_check  = year_to_match + "-" +   current_month + "-" + current_day
        logger.info("last_date_to_check is",last_date_to_check)


        logger.info("date and time:",date_time)

        logger.info("dob is",dob)
        if dob > date_time :
            # errors['dob'] = "Date of Birth cannot be in the future"
            msg = "Date of Birth cannot be in the future"
            raise serializers.ValidationError(msg)


        if dob > last_date_to_check:
            # errors['dob'] = "minimum 18 years required"
            msg = "minimum 16 years required"
            raise serializers.ValidationError(msg)



        word_list =list( DerogatoryWords.objects.all().values_list('word',flat=True))
        for word in word_list:
            if word in username:
                errors['username'] = "Derogatory words in username not allowed"
                break
     
        for character in username:
            if character not in check_list:
                errors['username'] = "Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters."
                break
        if alpha2code is not None:
            if alpha2code not in alpha2_list:
                errors['alpha2_list'] = 'not valid alpha2code'
        j = UserProfile.objects.filter(user__phone_verfied=True,nation__alpha2code=alpha2code,
        phone_number=phone_number)
        logger.info("j",j)


        if UserProfile.objects.filter(user__phone_verfied=True,nation__alpha2code=alpha2code
        ,phone_number=phone_number).exists():
            errors['phone_number'] = 'Number already exists'

        if phone_number.isdigit() is False:
            errors['phone_number'] = 'should be numbers only'
        try:
            validators.validate_password(password=password)
        except exceptions.ValidationError as e:
            errors['password'] = list(e.messages)

        if currency_id is not None:
            if currency_id not in id_list:
                errors['currency_id'] = 'not valid id'

        if errors:
            raise serializers.ValidationError(errors)
        logger.info("Vaidators passed")
        return super(UserSerializer, self).validate(data)



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)
    # token = serializers.CharField(max_length = 600)

    def validate(self, attrs):
        logger.info("attres is",attrs)
        authenticate_kwargs = {
            'username':attrs['username'],
            'password': attrs['password'],
        }
        try:
            authenticate_kwargs['request'] = self.context['request']
        except KeyError:
            pass
        logger.info("keyword argements is ",authenticate_kwargs)
        self.user = authenticate(**authenticate_kwargs)
        logger.info("user is ",self.user)

        if self.user is None :
            raise exceptions.AuthenticationFailed(

                'No active account found with the given credentials',
            )

        if self.user.is_active is False:
            raise serializers.ValidationError("your account is inactive")

        return attrs



class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ['user']




class ResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(
            required=True,
            validators=[UniqueValidator(queryset=User.objects.filter(email_verfied=True),message = 'email already exists')]
            
            )

class ResetPhoneSerializer(serializers.Serializer):
    alpha2code = serializers.CharField(max_length =10)
    phone_number = serializers.CharField(max_length=150,required=True,
                validators=[UniqueValidator(queryset=UserProfile.objects.filter(user__phone_verfied=True),message = 'phone number already exists')] )
   

    def validate(self, data):
        
        alpha2code = data.get('alpha2code')
       
    
        
        phone_number = data.get('phone_number')
        
        alpha2_list = Country.objects.all().values_list('alpha2code',flat=True)
        errors = dict()

        if alpha2code is not None:
            if alpha2code not in alpha2_list:
                errors['alpha2_list'] = 'not valid alpha2code'

        j = UserProfile.objects.filter(user__phone_verfied=True,nation__alpha2code=alpha2code)
        logger.info("j",j)
        if UserProfile.objects.filter(user__phone_verfied=True,nation__alpha2code=alpha2code
        ,phone_number=phone_number).exists():
            errors['phone_number'] = 'Number already exists'
        if phone_number.isdigit() is False:
            errors['phone_number'] = 'should be numbers only'
        if errors:
            raise serializers.ValidationError(errors)

        return super(ResetPhoneSerializer, self).validate(data)