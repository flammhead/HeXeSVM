from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib as sm
from hexesvm import iSeg_tools as _iseg

class MailNotifier():

    def __init__(self, mother_ui):

        ui = mother_ui

        # Extract default values via the loaded json file from the UI
        self.from_address = ui.defaults['email_from_address']
        self.recipients_info = ui.defaults['email_recipients_info']
        self.recipients_alarm = ui.defaults['email_recipients_alarm'] 
        self.sms_mail_address = ui.defaults['sms_mail_address'] 
        self.sms_numbers = ui.defaults['sms_recipients']
        self.sms_from_address = ui.defaults['sms_from_address']
        self.smtp_server = ui.defaults['email_smtp_server']


    def set_mail_recipient_info(self, recipient):
    
        self.recipients_info = recipient

    def set_mail_recipient_alarm(self, recipient):
    
        self.recipients_alarm = recipient

    def set_sms_recipient(self, recipient):
    
        self.sms_numbers = recipient

    
    def send_alarm(self, hv_channel, alarm_priority, alarm_kind):

        msg = MIMEMultipart()
        msg['From'] = self.from_address
        mail_subject = ""
        if alarm_priority == 1:
            mail_subject = "HeXe SVM info: "+hv_channel.name
            msg['To'] = self.recipients_info
            recipients_clean = self.recipients_info.replace(" ", "")
        elif alarm_priority == 2:
            mail_subject = "HeXe SVM ALARM: "+hv_channel.name
            msg['To'] = self.recipients_alarm
            recipients_clean = self.recipients_alarm.replace(" ", "")
        elif alarm_priority == 0:
            del msg
            return
        if alarm_kind == "single":
            mail_subject += " single trip"
        elif alarm_kind == "frequent":
            mail_subject += " frequent trip"
        elif alarm_kind == "kill":
            mail_subject += "HV KILL"

        msg['Subject'] = mail_subject
        message_string = "Possible HV trip detected.\n"
        message_string += "Name: "+hv_channel.name+"\n"
        message_string += "Voltage: "+str(hv_channel.voltage)+"\n"
        message_string += "Current: "+str(hv_channel.current)+"\n"
        msg.attach(MIMEText(message_string,'plain'))
        mail_conn = sm.SMTP(self.smtp_server)
        recipients_array = recipients_clean.split(",")
        mail_conn.sendmail(self.from_address, recipients_array, msg.as_string())
        return
        
    def send_sms(self, hv_channel, alarm_priority, alarm_kind):

        msg = MIMEMultipart()
        msg['From'] = self.from_address
        msg['To'] = self.sms_mail_address
        msg['Subject'] = "SMS"
        message_string = "PHONENUMBER: "
        message_string += self.sms_numbers
        message_string += "\nTEXT: "


        if alarm_priority == 1:
            message_string += "HeXe SVM info: "+hv_channel.name

        elif alarm_priority == 2:
            message_string += "HeXe SVM ALARM: "+hv_channel.name
        elif alarm_priority == 0:
            del msg
            return
        if alarm_kind == "single":
            message_string += " single trip"
        elif alarm_kind == "frequent":
            message_string += " frequent trip"
        elif alarm_kind == "kill":
            message_string += "HV KILL"


        msg.attach(MIMEText(message_string,'plain'))
        mail_conn = sm.SMTP(self.smtp_server)
        mail_conn.sendmail(self.from_address, self.sms_from_address, msg.as_string())

        return
