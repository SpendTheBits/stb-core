from django.apps import AppConfig


class xrplWalletConfig(AppConfig):
    name = 'xrpl_wallet'


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
            ChildItem(model='xrpl_wallet.xrplWallet'),
            ChildItem(model='xrpl_wallet.BitcoinWalletAccount'),
            
        ]),


        ParentItem('Transactions', children=[
            ChildItem(model='xrpl_wallet.STBTransaction'),
            ChildItem(model='xrpl_wallet.FundingTransaction'),
            
        ]),


        ParentItem('Configurations', children=[
            ChildItem(model='xrpl_wallet.Commission'),
            ChildItem(model='xrpl_wallet.AppConfiguration'),
            
        ]),


        ParentItem('Meta', children=[
            ChildItem(model='xrpl_wallet.Currency'),
            ChildItem(model='accounts.Country'),
            ChildItem(model='accounts.Logo'),
            ChildItem(model='xrpl_wallet.CentralWallet'),


            
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
