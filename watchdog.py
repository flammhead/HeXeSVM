from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib as sm
import time

from_address = "hexe@mpi-hd.mpg.de"
recipients_alarm = "hexe@mpi-hd.mpg.de, fjoerg@mpi-hd.mpg.de, hexe.shifter1@gmail.com"
#recipients_alarm = "hexe@mpi-hd.mpg.de, fjoerg@mpi-hd.mpg.de, hexe.shifter1@gmail.com, cichon@mpi-hd.mpg.de, eurin@mpi-hd.mpg.de, natascha.rupp@hotmail.de, natascha.rupp@mpi-hd.mpg.de"
# sms alarms not used right now
#sms_numbers = "+491774851456;+491748029906;+491637542725"
alarm_sent = False
heartbeat_file_name = "heartbeat.dat"
delta_t_max = 60

while True:

    time.sleep(10)
    file_hrtbt = open(heartbeat_file_name, "r")
    unix_stamp_file = float(file_hrtbt.read())
    unix_stamp_now = time.time()
    
    #if _w32g.FindWindow(None, "HeXeSVM") == 0:
    if unix_stamp_now - unix_stamp_file >= delta_t_max:
        if alarm_sent:
            continue
        msg = MIMEMultipart()
        msg['From'] = from_address
        msg['To'] = recipients_alarm
        msg['Subject'] = "HeXeSVM crashed!"
        message_string = "The HeXeSVM software is probably not running anymore!"
        msg.attach(MIMEText(message_string,'plain'))
        mail_conn = sm.SMTP("imap.mpi-hd.mpg.de")
        recipients_clean = recipients_alarm.replace(" ", "")
        recipients_array = recipients_clean.split(",")
        mail_conn.sendmail(from_address, recipients_array, msg.as_string())
        print("HeXeSVM not found! send alarm Email!")
        alarm_sent = True
    else:
        print("HeXeSVM is running")
        alarm_sent = False
    file_hrtbt.close()



'''
def send_sms(self, hv_channel, alarm_priority, alarm_kind):

    msg = MIMEMultipart()
    msg['From'] = self.from_address
    msg['To'] = "hexe@sms.mpi-hd.mpg.de"
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


    msg.attach(MIMEText(message_string,'plain'))
    mail_conn = sm.SMTP("imap.mpi-hd.mpg.de")
    mail_conn.sendmail(self.from_address, "hexe@sms.mpi-hd.mpg.de", msg.as_string())

    return
'''
