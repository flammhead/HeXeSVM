from PyQt5 import QtCore as _qc
import time
import socket as _soc


class HeartbeatSender(_qc.QThread):

    def __init__(self, mother_ui):

        _qc.QThread.__init__(self)
        # using localhost for now
        self.motherUI = mother_ui
        self.server_address = "127.0.0.1"
        self.server_port = 6667
        self.timeout_duration = 2
        self.update_interval = 5

        self.stop_sending = False
        self.connection_established = False
        
        
    def __delete__(self):
        self.socket.close()
        self.connection_established = False
        
    def connect_socket(self):
    
        try:
            self.socket = _soc.socket(_soc.AF_INET, _soc.SOCK_STREAM)
            self.socket.settimeout(self.timeout_duration)
            self.socket.connect((self.server_address, self.server_port))
    
        except(_soc.timeout):
            print("SOCKET TIME OUT!")
            self.connection_established = False
            self.socket.close()
            return False
            
        except(ConnectionRefusedError):
            print("HEARTBEAT CONNECTION REFUSED!")
            self.connection_established = False
            self.socket.close()
            return False
            
        self.connection_established = True
        return True
                
        
    def run(self):
        # This functino is meant to be run in a thread

        self.stop_sending = False
        while not self.stop_sending:
            if not self.connection_established:
                time.sleep(self.timeout_duration +1)
                self.connect_socket()
                continue
            # The current timestamp needs to be read from the main thread in order
            # to detect, if it froze to death!
            time_stamp = self.motherUI.time_stamp
            if time_stamp:
                time_stamp_str = str(time_stamp)
            else:
                continue
            
            try:
                self.socket.sendall(time_stamp_str.encode())
                return_data = (self.socket.recv(1024)).decode()
            except(_soc.timeout, ConnectionError):
                print("connection timeout!")
                self.connection_established = False
                continue
                
            if return_data != time_stamp_str:
                print("Wrong data recceived: ", return_data)
                self.connection_established = False
            else:
                self.connection_established = True
            time.sleep(self.update_interval)
        return
            
    def stop(self):
        self.stop_sending = True
        #self.terminate()
        return
            
