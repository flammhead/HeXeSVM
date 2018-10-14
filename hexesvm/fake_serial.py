import time
from random import gauss

class Serial:

    ## init(): the constructor.  Many of the arguments have default values
    # and can be skipped when calling the constructor.
    def __init__( self, port='COM1', baudrate = 19200, timeout=1,
                  bytesize = 8, parity = 'N', stopbits = 1, xonxoff=0,
                  rtscts = 0):
        self.name     = port
        self.port     = port
        self.timeout  = timeout
        self.parity   = parity
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.xonxoff  = xonxoff
        self.rtscts   = rtscts
        self.is_open  = True
        self._receivedData = ''
        self.sum_receivedData = ""

        self.time_last_command = 0
        
        self.u = [0,0]
        self.i = [0,0]
        self.v = [2,2]
        self.d = [0,0]
        self.ch_ramping = [False,False]
        self.chan_g_time = [0,0]

        
        self.ch_tripped = [False,False]
        self.ch_tripping_active = [True,True]
        self.ch_trip_interval = [60, 60]
        self.ch_last_trip = [0, 0]
        self.channel_state_bin = [256, 130] 
        self.ch_state = ["ON","ON"]

        
    def refresh_board(self):
    # this functino is activated when communication with board and refreshes all values
    # this function simulates the Hardware
        now_time = time.time()
        for index in range(2):
            t_delta = now_time - self.time_last_command
            if self.ch_state[index] == "H2L":
                if self.u[index] > self.d[index]:
                    self.u[index] = self.u[index] - self.v[index]*t_delta
                else:
                    self.u[index] = self.d[index]
                    self.ch_state[index] = "ON"
            elif self.ch_state[index] == "L2H":
                if self.u[index] < self.d[index]:
                    self.u[index] = self.u[index] + self.v[index]*t_delta
                else:
                    self.u[index] = self.d[index]
                    self.ch_state[index] = "ON"   
            if self.ch_tripping_active[index]:
                if self.ch_last_trip[index] == 0:
                    self.ch_last_trip[index] == now_time
                if now_time - self.ch_last_trip[index] > self.ch_trip_interval[index]:
                    self.u[index] = 0
                    self.ch_state[index] = "ERR"
                    self.ch_last_trip[index] = now_time
                
                
        self.time_last_command = now_time
        return

    ## isOpen()
    # returns True if the port to the Arduino is open.  False otherwise
    def isOpen( self ):
        return self._isOpen

    ## open()
    # opens the port
    def open( self ):
        self._isOpen = True

    ## close()
    # closes the port
    def close( self ):
        self._isOpen = False

    def write( self, string ):

        self._receivedData = string.decode()
        self.sum_receivedData += self._receivedData

    ## read()
    # reads n characters from the fake Arduino. Actually n characters
    # are read from the string _data and returned to the caller.
    def read( self, n=1 ):
        time.sleep(0.02)
        return self._receivedData.encode()
        
        
    def readline( self ):
        answer = "????"
        self.refresh_board()
        if not "\r\n" in self.sum_receivedData:
            return self.read()
        
        if self.sum_receivedData == "#\r\n":
            answer = "123456;1.23;1000;2mA"
        if self.sum_receivedData == "U1\r\n":
            answer = str(self.u[0])
        if self.sum_receivedData == "U2\r\n":
            answer = str(self.u[1])
        if self.sum_receivedData == "I1\r\n":
            answer = str(self.i[0])+"-06"
        if self.sum_receivedData == "I2\r\n":
            answer = str(self.i[1])+"-06"          
        if self.sum_receivedData == "M1\r\n":
            answer = "41"
        if self.sum_receivedData == "M2\r\n":
            answer = "42"  
        if self.sum_receivedData == "N1\r\n":
            answer = "41"
        if self.sum_receivedData == "N2\r\n":
            answer = "42"      
        if self.sum_receivedData == "D1\r\n":
            answer = str(self.d[0])  
        if self.sum_receivedData == "D2\r\n":
            answer = str(self.d[1])

        if "D1=" in self.sum_receivedData:
            self.d[0] = int(self.sum_receivedData.split('=')[1])
            answer = ""
        if "D2=" in self.sum_receivedData:
            self.d[1] = int(self.sum_receivedData.split('=')[1])
            answer = "" 
     
        if self.sum_receivedData == "V1\r\n":
            answer = str(self.v[0])         
        if self.sum_receivedData == "V2\r\n":
            answer = str(self.v[1])  
            
        if "V1=" in self.sum_receivedData:
            self.v[0] = int(self.sum_receivedData.split('=')[1])
            answer = ""
        if "V2=" in self.sum_receivedData:
            self.v[1] = int(self.sum_receivedData.split('=')[1])
            answer = ""    
        if "G1" in self.sum_receivedData:
            if self.ch_state[0] == "ON":
                if self.d[0] > self.u[0]:
                    answer = "S1=L2H"
                    self.ch_state[0] = "L2H"
                else:
                    answer = "S1=H2L"
                    self.ch_state[0] = "H2L"
                self.chan_g_time[0] = time.time()
                self.ch_ramping[0] = True
            else:
                answer = "S1="+self.ch_state[0]
        if "G2" in self.sum_receivedData:
            if self.ch_state[1] == "ON":
                if self.d[1] > self.u[1]:
                    answer = "S2=L2H"
                    self.ch_state[1] = "L2H"
                else:
                    answer = "S2=H2L"
                    self.ch_state[1] = "H2L"
                self.chan_g_time[1] = time.time()
                self.ch_ramping[1] = True
            else:
                answer = "S2="+self.ch_state[1]
        if self.sum_receivedData == "L1\r\n":
            answer = "10"   
        if self.sum_receivedData == "L2\r\n":
            answer = "10"                  
            
               
        if self.sum_receivedData == "T1\r\n":
          answer = self.channel_state_bin[0]          
        if self.sum_receivedData == "T2\r\n":
          answer = self.channel_state_bin[1]           
          
          
        if self.sum_receivedData == "S1\r\n":
          answer = "S1="+ self.ch_state[0]
          if self.ch_state[0] == "ERR":
              self.ch_state[0] = "ON"

        if self.sum_receivedData == "S2\r\n":
          answer = "S2="+self.ch_state[1]
          if self.ch_state[1] == "ERR":          
              self.ch_state[1] = "ON"
          
        if self.sum_receivedData == "A1\r\n":
          answer = "8"  
        if self.sum_receivedData == "A2\r\n":
          answer = "8"                                 
                                                                                     
        answer = str(answer) +"\r"
        self.sum_receivedData = ""
        time.sleep(0.03)
        return answer.encode()
