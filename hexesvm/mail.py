from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib as sm
from hexesvm import iSeg_tools as _iseg

class MailNotifier():

    def __init__(self):

        self.from_address = "hexe@mpi-hd.mpg.de"
        self.recipients = "hexe@mpi-hd.mpg.de"

    def set_mail_recipient(self, recipient):
    
        self.recipients = recipient
    
    def send_alarm(self, hv_channel, alarm_priority, alarm_kind):

        msg = MIMEMultipart()
        msg['From'] = self.from_address
        msg['To'] = self.recipients
        mail_subject = ""
        if alarm_priority == 1:
            mail_subject = "HeXe SVM info: "+hv_channel.name
        elif alarm_priority == 2:
            mail_subject = "HeXe SVM ALARM: "+hv_channel.name
        elif alarm_priority == 0:
            del msg
            return
        if alarm_kind == 1:
            mail_subject += " single trip"
        elif alarm_kind == 2:
            mail_subject += " frequent trip"

        msg['Subject'] = mail_subject
        message_string = "Possible HV trip detected.\n"
        message_string += "Name: "+hv_channel.name+"\n"
        message_string += "Voltage: "+str(hv_channel.voltage)+"\n"
        message_string += "Current: "+str(hv_channel.current)+"\n"
        msg.attach(MIMEText(message_string,'plain'))
        mail_conn = sm.SMTP("imap.mpi-hd.mpg.de")
        mail_conn.sendmail(self.from_address, self.recipients, msg.as_string())
        return
        
