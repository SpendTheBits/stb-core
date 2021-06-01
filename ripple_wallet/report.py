from .models import *
from accounts.models import *
from withdraw.models import *
import datetime
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import datetime, timedelta

def send_report_email(context,current_date):
    
    subject="Transactions report on "+str(current_date)
    email_html_message = render_to_string('email/transaction_report.html', context)
    receiver_email=AppConfiguration.objects.all().first().email
    logger.info("receiver_email  is",receiver_email)
    msg = EmailMultiAlternatives(
    subject,
    'Transaction Report',
    settings.FROM_EMAIL,
    [receiver_email]
    )
    msg.attach_alternative(email_html_message, "text/html")
    try:
        msg.send()
        logger.info("sent mail worked ")
    except Exception as e:
        logger.info("error in sending mail in @24 is",str(e))
        return False
    return True
def send_transaction_report():
    current_date=datetime.datetime.now().date()
    # current_date="2020-11-13"
    # one_week_ago = datetime.datetim.today() - timedelta(days=7)
    logger.info('current_date=',current_date)
    current_stb_transactions=STBTransaction.objects.filter(created_date__date=current_date)
    
    logger.info('current_stb_transactions=',current_stb_transactions)
    context={
        "current_date":current_date
    }
    if current_stb_transactions:
        context['no_stb_transaction']=False
    else:
        context['no_stb_transaction']=True
        logger.info('No wallet Transactions done')
    context['stb_transaction']=current_stb_transactions

    current_fund_transactions=FundingTransaction.objects.filter(created_date__date=current_date)
    logger.info('current_fund_transactions=',current_fund_transactions)
    
    if current_fund_transactions:
        context['no_fund_transaction']=False
    else:
        context['no_fund_transaction']=True
        logger.info('No Fund transactions done')
    context['fund_transaction']=current_fund_transactions

    current_withdrawal_transc=WithDrawalTransaction.objects.filter(created_date__date=current_date)
    if current_withdrawal_transc:
        context['no_withdrawal_transaction']=False
    else:
        context['no_withdrawal_transaction']=True
        logger.info('no withdrawal transaction')
    context['withdrawal_transaction']=current_withdrawal_transc

    current_ledger=Ledger.objects.filter(created_date__date=current_date)
    context['no_ledger']=False if current_ledger else True
    context['current_ledger']=current_ledger

    current_bitcoint_ledger=BitcoinNetworkLedger.objects.filter(created_date__date=current_date)
    
    context['no_bitcoin_ledger']=False if current_bitcoint_ledger else True
    context['current_bitcoint_ledger']=current_bitcoint_ledger

    
    try:
        send_report_email(context,current_date)
    except Exception as e:
        logger.info('transaction report mail send error',str(e))

    return context