from django.apps import AppConfig


class RippleWalletConfig(AppConfig):
    name = 'ripple_wallet'


from suit.apps import DjangoSuitConfig
from suit.menu import ParentItem,ChildItem

class SuitConfig(DjangoSuitConfig):
    # layout = 'horizontal'
    layout = 'horizontal'
    menu=(
        
        ParentItem('Account', children=[
            ChildItem(model='accounts.User'),
            ChildItem(model='accounts.UserProfile'),
            
        ]),

        ParentItem('Wallet', children=[
            ChildItem(model='ripple_wallet.RippleWallet'),
            ChildItem(model='ripple_wallet.BitcoinWalletAccount'),
            
        ]),


        ParentItem('Transactions', children=[
            ChildItem(model='ripple_wallet.STBTransaction'),
            ChildItem(model='ripple_wallet.FundingTransaction'),
            
        ]),


        ParentItem('Configurations', children=[
            ChildItem(model='ripple_wallet.Commission'),
            ChildItem(model='ripple_wallet.AppConfiguration'),
            
        ]),


        ParentItem('Meta', children=[
            ChildItem(model='ripple_wallet.Currency'),
            ChildItem(model='accounts.Country'),
            ChildItem(model='accounts.Logo'),
            ChildItem(model='ripple_wallet.CentralWallet'),


            
        ]),

        ParentItem('User Attempts', children=[
            ChildItem('Logs',url='/admin/axes/accesslog/'),
            ChildItem('wrong attempts',url='/admin/axes/accessattempt/'),
            
        ]),

        ParentItem('Two Factor Authentication', children=[
            ChildItem('Phone Devices',url='/admin/two_factor/phonedevice/'),
            ChildItem('OTP Device',url='/admin/otp_totp/totpdevice/'),
            
        ]),

        )










def ready(self):
    super(SuitConfig, self).ready()
