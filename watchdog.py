from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib as sm
import time
import socket as _soc
import os


from_address = "hexe@mpi-hd.mpg.de"
#recipients_alarm = "fjoerg@mpi-hd.mpg.de, hexe.shifter1@gmail.com"
recipients_alarm = "hexe@mpi-hd.mpg.de, fjoerg@mpi-hd.mpg.de, hoetzsch@mpi-hd.mpg.de, mona.piotter@mpi-hd.mpg.de, robert.hammann@mpi-hd.mpg.de, hexe.shifter1@gmail.com"
# sms alarms not used right now
#sms_numbers = "+491774851456;+491748029906;+491637542725"
alarm_sent = False
delta_t_max = 60

address = "127.0.0.1"
port = 6667
allowed_clients = (("127.0.0.1"))
socket = _soc.socket(_soc.AF_INET, _soc.SOCK_STREAM)
socket.bind((address, port))
socket.settimeout(10)
clientsocket = None
last_received_time = 0

#startup delay
start_up_delay = 60
print("watchdog start-up delay (seconds): ", start_up_delay)
time.sleep(start_up_delay)



while True:

    socket.listen(5)
    
    if clientsocket:
    
        data = ''
        try: 
            data = clientsocket.recv(1024).decode()
            clientsocket.send(data.encode())
            last_received_time = float(data)       
           
        except(ValueError):
            print("WRONG DATA RECEIVED! ", data)
            clientsocket.close()
            clientsocket = None               
            
        except OSError as e:
            print(e)
            clientsocket.close()
            clientsocket = None   
    
    else:
        try:
            clientsocket, address = socket.accept()
            print("incomming connection found from" + str(address[0]))

            if not (address[0] in allowed_clients):
                print("Connection refused from: ", address[0])
                clientsocket.close()
                clientsocket = None
                continue    
            else:
                continue        
                    
        except(_soc.timeout):
            print("timed out")


    unix_stamp_now = time.time()

    if unix_stamp_now - last_received_time >= delta_t_max:
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
        print("HeXeSVM Heartbeat outdated! send alarm Email!")
        alarm_sent = True
    else:
        print("HeXeSVM Heartbeat, up to date")
        alarm_sent = False                    
        



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

