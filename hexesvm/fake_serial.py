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
        self._data = "It was the best of times.\nIt was the worst of times.\n"
        
        self.v1 = "002"
        self.v2 = "002"
        self.d1 = "0000"
        self.d2 = "0000"
        self.chan1_down = False
        self.chan2_down = False

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
        time.sleep(0.2)
        return self._receivedData.encode()
        
        
    def readline( self ):
        answer = "????"
        
        if not "\r\n" in self.sum_receivedData:
            return self.read()
        
        if self.sum_receivedData == "#\r\n":
            answer = "123456;1.23;1000;2mA\r"
        if self.sum_receivedData == "U1\r\n":
            answer = str(int(gauss(1111,1)))+"\r"
        if self.sum_receivedData == "U2\r\n":
            answer = str(int(gauss(-2222,1)))+"\r"
        if self.sum_receivedData == "I1\r\n":
            answer = str(int(gauss(23,1)))+"-06\r"
        if self.sum_receivedData == "I2\r\n":
            answer = str(int(gauss(23,1)))+"-06\r"          
        if self.sum_receivedData == "M1\r\n":
            answer = "41\r"
        if self.sum_receivedData == "M2\r\n":
            answer = "42\r"  
        if self.sum_receivedData == "N1\r\n":
            answer = "41\r"
        if self.sum_receivedData == "N2\r\n":
            answer = "42\r"      
        if self.sum_receivedData == "D1\r\n":
            answer = str(self.d1)+"\r"  
        if self.sum_receivedData == "D2\r\n":
            answer = str(self.d2)+"\r"  

        if "D1=" in self.sum_receivedData:
            self.d1 = self.sum_receivedData.split('=')[1]
            answer = "D1="+self.d1+"\r"
        if "D2=" in self.sum_receivedData:
            self.d2 = self.sum_receivedData.split('=')[1]
            answer = "D2="+self.d2+"\r" 
     
        if self.sum_receivedData == "V1\r\n":
            answer = str(self.v1)+"\r"      
        if self.sum_receivedData == "V2\r\n":
            answer = str(self.v2)+"\r"  
            
        if "V1=" in self.sum_receivedData:
            self.v1 = self.sum_receivedData.split('=')[1]
            answer = "V1="+self.v1+"\r"
        if "V2=" in self.sum_receivedData:
            self.v2 = self.sum_receivedData.split('=')[1]
            answer = "V2="+self.v2+"\r"    
        if "G1" in self.sum_receivedData:
            answer = "S1=H2L\r"
            self.chan1_down = True
        if "G2" in self.sum_receivedData:
            answer = "S2=H2L\r"
            self.chan2_down = True          
        if self.sum_receivedData == "L1\r\n":
            answer = "10\r"   
        if self.sum_receivedData == "L2\r\n":
            answer = "10\r"                     
        if self.sum_receivedData == "T1\r\n":
          answer = "255\r"          
        if self.sum_receivedData == "T2\r\n":
          answer = "128\r"         
        if self.sum_receivedData == "S1\r\n":
          answer = "S1=ON\r"    
          if self.chan1_down:
          	answer = "S1=H2L"
        if self.sum_receivedData == "S2\r\n":
          answer = "S2=ON\r" 
          if self.chan2_down:
          	answer = "S2=H2L"                                     
        if self.sum_receivedData == "A1\r\n":
          answer = "8\r"  
        if self.sum_receivedData == "A2\r\n":
          answer = "8\r"                                 
                                                                                     
        
        self.sum_receivedData = ""
        time.sleep(0.1)
        return answer.encode()
