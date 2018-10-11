from PyQt5 import QtCore as _qc
#from hexesvm import iSeg_tools as _iseg
import time


class MonitorIsegModule(_qc.QThread):

    def __init__(self, hv_module):
        _qc.QThread.__init__(self)
        self.module = hv_module
        self.stop_looping = False
        
    def run(self):
        # This functino is meant to be run in a thread
        self.module.stop_thread = False        
        n_read_all = 5
        i = n_read_all
        self.module.board_occupied = True
        self.stop_looping = False
        while not self.stop_looping:
            #print(self.module.board_occupied, self.stop_looping, self.module.stop_thread)
            if not self.module.is_connected:
                time.sleep(1)
                continue
            for channel in self.module.child_channels:
                # make the channel to update its voltage and current information
                if self.module.stop_thread:
                    self.stop()
                    
                channel.read_voltage()
                if self.module.stop_thread:
                    self.stop()              
                      
                channel.read_current()
                # if this was the n_read_all th iteration read all other info
                if i >= n_read_all:
                    print("READALL")
                    if self.module.stop_thread:
                        self.stop()         
                               
                    channel.read_voltage_limit()
                    if self.module.stop_thread:
                        self.stop()         
                                             
                    channel.read_current_limit()
                    if self.module.stop_thread:
                        self.stop()         
                                             
                    channel.read_set_voltage()
                    if self.module.stop_thread:
                        self.stop()         
                                             
                    channel.read_ramp_speed()
                    if self.module.stop_thread:
                        self.stop()         
                                             
                    channel.read_trip_current()
                    if self.module.stop_thread:
                        self.stop()      
                                                
                    channel.read_device_status()
                    if self.module.stop_thread:
                        self.stop()   
                        
                    channel.read_status()
                    if self.module.stop_thread:
                        self.stop()   
                    channel.read_auto_start()
            if i >= n_read_all:
                i = 0
            i+=1    
        return
            
    def stop(self):
        self.module.board_occupied = False
        self.stop_looping = True
        self.terminate()
        return
        
            
