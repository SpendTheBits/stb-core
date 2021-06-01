from rest_framework import exceptions,serializers
from rest_framework.validators import UniqueValidator,UniqueTogetherValidator
from .models import *
from datetime import date


from datetime import datetime


class KycSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    dob = serializers.CharField(required=False)
    document_type = serializers.CharField(required=False)
    document_front = serializers.FileField(required=False)
    document_back = serializers.FileField(required=False)
    selfie = serializers.FileField(required=False)



    def validate(self, data):

        request = self.context.get('request')
        user = request.user
        logger.info("date.today() is",date.today())
        attempt_count = KycAttempt.objects.filter(user=user,created_date__date=date.today()).count()   

        logger.info("attempt_count is",attempt_count)

        if attempt_count >= 15:
            raise serializers.ValidationError("reached limit of "+str(attempt_count)+ " attempts per day")
        return data