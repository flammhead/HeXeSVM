import time
from random import gauss
import numpy as _np

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
        self.echoed = False
        
        self.time_last_command = 0

        n_channels = 0
        # Simulate a NHQ module at COM1
        if port=="COM1":
            self.n_channels = 2
        # For COM3 lets take an NHR module
        elif port=="COM3":
            self.n_channels = 4
 
        self.u = self.n_channels*[0]
        self.i = self.n_channels*[0]
        if port=="COM1":
            self.r = self.n_channels*[40.5e6]
        if port=="COM3":
            self.r = [40e9, 40e9, _np.inf, _np.inf]
        self.v = self.n_channels*[2]
        self.d = self.n_channels*[0]
        self.ch_ramping = self.n_channels*[False]
        self.ch_ramp_up = self.n_channels*[False]
        self.ch_ramp_down = self.n_channels*[False]
        self.chan_g_time = self.n_channels*[0]
        self.ch_tripped = self.n_channels*[False]
        self.ch_tripping_active = self.n_channels*[False]
        self.ch_trip_interval = self.n_channels*[60]
        self.ch_last_trip = self.n_channels*[0]
        self.channel_state_bin = self.n_channels*[170] 
        self.ch_state = self.n_channels*["ON"]
        self.hv_on = self.n_channels*[False]
        self.is_positive = self.n_channels*[False]
            
        
    def refresh_board(self):
    # this functino is activated when communication with board and refreshes all values
    # this function simulates the Hardware
        now_time = time.time()
        for index in range(self.n_channels):
            t_delta = now_time - self.time_last_command
            if self.ch_state[index] == "H2L":
                if self.u[index] > self.d[index]:
                    self.u[index] = self.u[index] - self.v[index]*t_delta
                    self.ch_ramp_down[index] = True
                else:
                    self.u[index] = self.d[index]
                    self.ch_state[index] = "ON"
                    self.ch_ramp_down[index] = False
            elif self.ch_state[index] == "L2H":
                if self.u[index] < self.d[index]:
                    self.u[index] = self.u[index] + self.v[index]*t_delta
                    self.ch_ramp_up[index] = True
                else:
                    self.u[index] = self.d[index]
                    self.ch_state[index] = "ON"
                    self.ch_ramp_up[index] = False
            if self.ch_tripping_active[index]:
                if self.ch_last_trip[index] == 0:
                    self.ch_last_trip[index] == now_time
                if now_time - self.ch_last_trip[index] > self.ch_trip_interval[index]:
                    self.u[index] = 0
                    self.ch_state[index] = "ERR"
                    self.ch_last_trip[index] = now_time
                    self.ch_tripped[index] = True
            # Set the current according to the resistance
            self.i[index] = self.u[index] / self.r[index]
                
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
            
       
        if self.port == "COM1":

            ######################
            # NHQ virtualization #
            ######################
    
            if self.sum_receivedData == "#\r\n":
                answer = "487472;1.23;1000;2mA"
            if self.sum_receivedData == "U1\r\n":
                answer = str(self.u[0])
            if self.sum_receivedData == "U2\r\n":
                answer = str(self.u[1])
            if self.sum_receivedData == "I1\r\n":
                answer = str(int(self.i[0]*1e6))+"-06"
            if self.sum_receivedData == "I2\r\n":
                answer = str(int(self.i[1]*1e6))+"-06"          
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
                        self.ch_ramping[0] = True
                    elif self.d[0] < self.u[0]:
                        answer = "S1=H2L"
                        self.ch_state[0] = "H2L"
                        self.ch_ramping[0] = True
                    else:
                        answer = "S1=ON"
                        self.ch_state[0] = "ON"
                        self.ch_tripped[0] = False
                    self.chan_g_time[0] = time.time()
                    
                else:
                    answer = "S1="+self.ch_state[0]
            if "G2" in self.sum_receivedData:
                if self.ch_state[1] == "ON":
                    if self.d[1] > self.u[1]:
                        answer = "S2=L2H"
                        self.ch_state[1] = "L2H"
                        self.ch_ramping[1] = True
                    elif self.d[1] < self.u[1]:
                        answer = "S2=H2L"
                        self.ch_state[1] = "H2L"
                        self.ch_ramping[1] = True
                    else:
                        answer = "S2=ON"
                        self.ch_state[1] = "ON"
                    self.chan_g_time[1] = time.time()
    
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
                  self.ch_tripped[0] = False
    
            if self.sum_receivedData == "S2\r\n":
              answer = "S2="+self.ch_state[1]
              if self.ch_state[1] == "ERR":          
                  self.ch_state[1] = "ON"
                  self.ch_tripped[1] = False
              
            if self.sum_receivedData == "A1\r\n":
              answer = "8"  
            if self.sum_receivedData == "A2\r\n":
              answer = "8"                                 

        elif self.port == "COM3":

            if self.echoed == False:
                self.echoed = True
                return self.sum_receivedData.encode()
            self.echoed = False
            
            ######################
            # NHR virtualization #
            ######################
            
            if "(@" in self.sum_receivedData:
                # Extract the channel number on which to act the command
                split_command = self.sum_receivedData.split('(@')
                channel_trail = split_command[1]
                channel_number = int(channel_trail.split(')')[0])

            
            if self.sum_receivedData == "*IDN?\r\n":
                answer = "iseg Spezialelektronik GmbH,NR042060r4050000200,8200002,1.12"
            if self.sum_receivedData == "*OPC?\r\n":
                answer = "1"
                
            if "MEAS:VOLT?" in self.sum_receivedData:
                answer = str(self.u[channel_number]/1e3)+"E3V"
            if "MEAS:CURR?" in self.sum_receivedData:
                answer = str(self.i[channel_number]*1e3)+"E-3A"
            
            if "READ:VOLT:LIM?" in self.sum_receivedData:
                answer = "41"
            if "READ:CURR:LIM?" in self.sum_receivedData:
                answer = "44"            

            if "READ:VOLT?" in self.sum_receivedData:
                answer = str(self.d[channel_number]/1e3)+"E3V"  

            if ":VOLT " in self.sum_receivedData:
                if " ON,(" in self.sum_receivedData:
                    # Turn on HV channel
                    self.hv_on[channel_number] = True
                    pass
                elif " OFF,(" in self.sum_receivedData:
                    # Turn off HV channel
                    self.hv_on[channel_number] = False
                    pass
                elif "EMCY OFF,(":
                    # Turn off channel without ramp set emcy state
                    pass
                else:
                    value_trail = self.sum_receivedData.split('VOLT ')[1]
                    value = int(value_trail.split(',(')[0])
                    self.d[channel_number] = value
            
            if ":VOLT " in self.sum_receivedData and not ("ON" in self.sum_receivedData or "OFF" in self.sum_receivedData):
                value_trail = self.sum_receivedData.split('VOLT ')[1]
                value = int(value_trail.split(',(')[0])
                self.d[channel_number] = value
                answer = "1"
         
         
            if ":CONF:RAMP:VOLT:UP?" in self.sum_receivedData:
                answer = str(self.v[channel_number]/1e3)+"E3V/s"   

            if ":CONF:RAMP:VOLT:UP " in self.sum_receivedData: 
                value_trail = self.sum_receivedData.split(':CONF:RAMP:VOLT:UP ')[1]
                value = int(value_trail.split(',(')[0])
                self.v[channel_number] = value
                answer = "1"
            if ":CONF:RAMP:VOLT:DO " in self.sum_receivedData:
                value_trail = self.sum_receivedData.split(':CONF:RAMP:VOLT:DO ')[1]
                value = int(value_trail.split(',(')[0])
                self.v[channel_number] = value
                answer = "1"
                

            if ":VOLT ON,(@" in self.sum_receivedData:
                channel = int(self.sum_receivedData[11])
                self.hv_on[channel] = True
                if self.d[channel] != self.u[channel]:
                    self.ch_ramping[0] = True
                self.chan_g_time[0] = time.time()
                answer = "1"

            if ":CONF:OUT:POL " in self.sum_receivedData:
                value_trail = self.sum_receivedData.split(':CONF:OUT:POL ')[1]
                value = value_trail.split(',(')[0]
                if not self.hv_on[channel_number]:
                    if abs(self.u[channel_number]) < 0.002 * 6E3:
                        self.is_positive[channel_number] = value == "p"
                        answer = "1"                
                else:
                    answer = "0"            
              
            if ":READ:CHAN:STAT?" in self.sum_receivedData:
                #calculate the binary state
                POS = self.is_positive[channel_number]
                HVON = self.ch_state[channel_number]=='ON'
                RAMP = self.ch_ramping[channel_number]
                TRIP = self.ch_tripped[channel_number]
                RUP = self.ch_ramp_up[channel_number]
                RDOWN = self.ch_ramp_down[channel_number]
                
                bin_state = _np.array((POS,0,0,HVON,RAMP,0,0,0,
                                      0,0,0,0,0,TRIP,0,0,
                                      0,0,0,RUP,RDOWN,0,0,0,
                                      0,0,0,0,0,0,0,0))
                int_state = 0
                for idx, byte in enumerate(bin_state):
                    int_state += byte*(2**idx)
                
                answer = int_state

            # Since for the NHR board, we don't need to wait for each character
            # To echo, we prepend the echo to the answer of the command
            answer = answer


                                                                                     
        answer = str(answer) +"\r"
        self.sum_receivedData = ""
        time.sleep(0.03)
        return answer.encode()
