import os
import environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
# reading .env file
environ.Env.read_env()

PRODUCTION_ENV=env('PROD') #Change this to flip between DEV AND PROD
TEST_ENV = not PRODUCTION_ENV

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR,'templates')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('secret')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = not PRODUCTION_ENV
# DEBUG = False

ALLOWED_HOSTS = ['*']
AUTH_USER_MODEL = 'accounts.User'

# Application definition

INSTALLED_APPS = [
    'xrpl_wallet.apps.SuitConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'nested_admin',
    'rest_framework',
    'rangefilter',
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'django_rest_passwordreset',
    'import_export',
    'corsheaders',
    'admin_reorder',
    'xrpl_wallet',
    "push_notifications",
    "fcm_django",
    'payid',
    'withdraw',
    'kyc',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'admin_reorder.middleware.ModelAdminReorder',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'spend_the_bits.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spend_the_bits.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

BITGO_WALLET=env('bitgo_wallet')
BITGO_URL=env('bitgo_url')
BITGO_EXPRESS_URL=env('bitgo_express_url')
BITGO_KEY = env('bitgo_key')
BITGO_COIN=env('bitgo_coin')
PAYID_URI_DOMAIN = env('payid_uri_domain')
CURRENT_API_URL = env('api_url')
xrpl_SUBMIT_SERVER = env('xrpl_net')
BITGO_PASSPHRASE=env('bitgo_passphrase')
SMS_APP_HASH = env('sms_hash')
WITHDRAW_TRANSACTION_URL="https://live.blockcypher.com/btc-testnet/tx/"
FUND_TRANSACTION_URL="https://live.blockcypher.com/btc-testnet/tx/"
STB_TRANSACTION_URL="https://test.bithomp.com/explorer/"
KYC_URL = env('kyc_url')
KYC_USERNAME =env('kyc_usr')
KYC_PASSWORD = env('kyc_pswd')


DATABASES = {
    'default': {
        'ENGINE': env('db_engine'),
        'NAME':  env('db_name'),
        'USER': env('db_user'),
        'PASSWORD': env('db_pswd'),
        'HOST': env('db_host'),
        'PORT': env('db_port'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Montreal'

USE_I18N = True

USE_L10N = True

USE_TZ = True
CORS_ORIGIN_ALLOW_ALL = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/


STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static_files"),
]

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_ROOT= os.path.join(BASE_DIR, 'media/')
APNS_ROOT= os.path.join(BASE_DIR, env('apns_root'))
MEDIA_URL= "/media/"




REST_FRAMEWORK = {

    'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
                              ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}


from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    }



ADMIN_REORDER = (
# First group
{'app': 'accounts', 'label': 'Account',
'models': ('accounts.User','accounts.UserProfile')
},
# Second group: same app, but different label
{'app': 'xrpl_wallet', 'label': 'Wallet',
'models': ('xrpl_wallet.xrplWallet','xrpl_wallet.BitcoinWalletAccount',

)},
# Second group: same app, but different label
{'app': 'xrpl_wallet', 'label': 'Transactions',
'models': ('xrpl_wallet.STBTransaction','xrpl_wallet.FundingTransaction',
'withdraw.WithDrawalTransaction',
'withdraw.Ledger',
'withdraw.BitcoinNetworkLedger',
)
},
# Second group: same app, but different label
{'app': 'xrpl_wallet', 'label': 'Configurations',
'models':
('xrpl_wallet.Commission',
'xrpl_wallet.AdminEmail',
'xrpl_wallet.AppNotification',
'accounts.DerogatoryWords',
'withdraw.NetworkFees',
'withdraw.WithdrawLimit',
'withdraw.WithdrawApproval',
'xrpl_wallet.AppConfiguration',

)
},


{'app': 'xrpl_wallet', 'label': 'BTC Currency Issuer Wallet',
'models': (
'xrpl_wallet.CentralWallet',
)
},


{'app': 'xrpl_wallet', 'label': 'Commission Wallet',
'models': (
'xrpl_wallet.CommissionWallet',
)
},


{'app': 'xrpl_wallet', 'label': 'Pending Due to Trust Line',
'models': (

'xrpl_wallet.PendingTransactions',
'xrpl_wallet.PendingFundTransactions',
)
},


{'app': 'xrpl_wallet', 'label': 'Payid',
'models': (

'payid.CryptoAddress',
'payid.PayId',
)
},

{'app': 'xrpl_wallet', 'label': 'Meta',
'models': (

'xrpl_wallet.Currency',
'accounts.Country',
'xrpl_wallet.ExchangeRate',
'accounts.Version',

'push_notifications.GCMDevice',
# 'push_notifications.APNSDevice',

'xrpl_wallet.FundingAddress',
'xrpl_wallet.TransactionOtpAttempt',
'withdraw.WithdrawTransactionOtpAttempt',
'kyc.KycAttempt',
'kyc.KycApplication',

)
},




)



EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
FROM_EMAIL = env('email_from')



EMAIL_PROVIDER = env('email_provider')

EMAIL_USE_TLS = True
EMAIL_HOST = env('email_host')
EMAIL_HOST_USER = env('email_user')
EMAIL_HOST_PASSWORD = env('email_password')
EMAIL_PORT = int(env('email_port'))
xrpl_SERVER=env('xrpl_server')

#twilio key
ACCOUNT_SECURITY_API_KEY=env('twilio_key')
TWILIO_ACCOUNT_SID = env('twilio_account_sid')
TWILIO_AUTH_TOKEN = env('twilio_auth_token')
TWILIO_SERVICE_SID = env('twilio_service_sid')


#CELERY
CELERY_BROKER_URL = env('celery_url')
CELERY_RESULT_BACKEND = env('celery_backend')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'


PUSH_NOTIFICATIONS_SETTINGS = {
        "FCM_API_KEY": env('fcm_api_key'),
         "APNS_USE_SANDBOX": False,
        "APNS_CERTIFICATE":APNS_ROOT,
  
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800