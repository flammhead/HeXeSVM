from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib as sm
from hexesvm import iSeg_tools as _iseg

class MailNotifier():

    def __init__(self):

        self.from_address = "hexe@mpi-hd.mpg.de"
        self.recipients = "florian.joerg@mpi-hd.mpg.de"

    def set_mail_recipient(self, recipient):
    
        self.recipients = recipient
    
    def send_alarm(self, hv_channel, alarm_mode):

        msg = MIMEMultipart()
        msg['From'] = self.from_address
        msg['To'] = self.recipients
        if alarm_mode == 1:
            msg['Subject'] = "HeXe SVM info: "+hv_channel.name+" single trip"
        elif alarm_mode == 2:
            msg['Subject'] = "HeXe SVM ALARM: "+hv_channel.name+" frequent trip"
        else:
            msg['Subject'] = "HeXe SVM: "+hv_channel.name

        message_string = "Possible HV trip detected.\n"
        message_string += "Name: "+hv_channel.name+"\n"
        message_string += "Voltage: "+str(hv_channel.voltage)+"\n"
        message_string += "Current: "+str(hv_channel.current)+"\n"
        msg.attach(MIMEText(message_string,'plain'))
        mail_conn = sm.SMTP("imap.mpi-hd.mpg.de")
        mail_conn.sendmail(self.from_address, self.recipients, msg.as_string())
        
