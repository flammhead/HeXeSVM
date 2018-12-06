from PyQt5 import QtCore as _qc
#from hexesvm import iSeg_tools as _iseg
import time

import socket
import sys
import os
import time
import datetime



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# using localhost for now
host = "127.0.0.1"
port = 6667
s.bind((host, port))

allowed_clients = (("149.217.1.94", "149.217.9.245"))

s.listen(5)
w_log("start listening")
clientsocket, address = s.accept()
w_log("incomming connection found from" + str(address[0]))

if address[0]  in allowed_clients:

        data = ''
        data = clientsocket.recv(1024).decode()
        if data == "get_buffer_list":
                file_folder_list = os.listdir(buffer_path)
                folder_list = []
                for entry in file_folder_list:
                        if not os.path.isdir(buffer_path + "/" + entry):
                                continue
                        folder_list.append(entry)

                clientsocket.send(str(len(folder_list)).encode())
                w_log("sending " + str(len(folder_list)) + " folder names")
                for folder in folder_list:
                        w_log(folder)
                        clientsocket.send(folder.encode())
                        time.sleep(0.1)

w_log("closing connection")
s.close()


class HeartbeatSender(_qc.QThread):

    def __init__(self):
        _qc.QThread.__init__(self)

        self.stop_sending = False
        
    def run(self):
        # This functino is meant to be run in a thread

        self.stop_sending = False
        while not self.stop_sending:


        return
            
    def stop(self):
        self.stop_sending = True
        #self.terminate()
        return
            
