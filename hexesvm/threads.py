from PyQt5 import QtCore as _qc
from PyQt5 import QtGui as _qg
#from hexesvm import iSeg_tools as _iseg
import time
import pandas as _pd
import numpy as _np


class MonitorIsegModule(_qc.QThread):

    def __init__(self, hv_module):
        _qc.QThread.__init__(self)
        self.module = hv_module
        self.stop_looping = False
        self.module.stop_thread = False

        
    def run(self):
        # This functino is meant to be run in a thread
        n_read_all = 5
        i = n_read_all
        
        while self.module.board_occupied:
            if self.module.stop_thread:
                self.stop()
                break
            time.sleep(0.2)
          
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
                    break
                channel.read_voltage()
                if self.module.stop_thread:
                    self.stop()              
                    break
                channel.read_current()
                # Check if current and voltage still fit the expectation
                channel.check_software_trip()
                
                # if this was the n_read_all th iteration read all other info
                if i >= n_read_all:
                    if self.module.stop_thread:
                        self.stop()         
                        break                
                    channel.read_set_voltage()
                    if self.module.stop_thread:
                        self.stop()         
                        break                
                    channel.read_ramp_speed()
                    if self.module.stop_thread:
                        self.stop()   
                        break

                    if channel.module.type == "NHQ":
                        channel.read_status()                                 
                        
                    if self.module.stop_thread:
                        self.stop()         
                        break  
                    channel.read_voltage_limit()
                    if self.module.stop_thread:
                        self.stop()         
                        break                
                    channel.read_current_limit()
                    if self.module.stop_thread:
                        self.stop()         
                        break                

                    if channel.module.type == "NHQ":    
                        channel.read_trip_current()
                        
                    if self.module.stop_thread:
                        self.stop()      
                        break
                    channel.read_device_status()
                    if self.module.stop_thread:
                        self.stop()
                        break
                        
                    if channel.module.type == "NHQ":
                        channel.read_auto_start()
                        
            if i >= n_read_all:
                i = 0
            i+=1    
        return
            
    def stop(self):
        self.module.board_occupied = False
        self.stop_looping = True
        self.module.reader_thread = None
        #self.terminate()
        return

class ScheduleRampIsegModule(_qc.QThread):

    ramp_hv = _qc.pyqtSignal('PyQt_PyObject', 'PyQt_PyObject')
    highlight_row = _qc.pyqtSignal('PyQt_PyObject')
    change_hv_settings = _qc.pyqtSignal('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')

    def __init__(self, gui):
        _qc.QThread.__init__(self)
        self.gui = gui
        #self.stop_looping = False
        self.is_running = False
        self.performing_step = False
        self.stop_signal = False
        
        
    def run(self):

        if not self.stop_signal:
            
            self.is_running = True
            self.rampTableCurrentIndex = 0

            for i in range(self.gui.rampTable.rowCount()):
                time.sleep((float(self.gui.rampTable.item(self.rampTableCurrentIndex,0).text())*60.))
                self.ramp_schedule_step()
            #self.gui.stop_ramp_schedule()
            
        return

    def ramp_schedule_step(self):
    
        if not self.gui.locker.lock_state:        
            print("Interlock is triggered!")
            self.stop()
            return
        if self.stop_signal:
            return
        self.performing_step = True
        # we now need to proceed changing/ramping a new row from the table!
        voltages = []
        speeds = []
        channels_needing_change = []
        #extract the information
        curr_row = self.rampTableCurrentIndex
        self.highlight_row.emit(curr_row)
        for jdx in range(len(self.gui.channel_order_dict)):
            this_channel = self.gui.channel_order_dict[jdx][1].replace(' ','')
            voltages.append(self.gui.rampTableDataPd["U("+this_channel+")"][curr_row])
            speeds.append(self.gui.rampTableDataPd["V("+this_channel+")"][curr_row])

        print(voltages)
        print(speeds)         
            
        for i in range(len(self.gui.channel_order_dict)):
            if self.stop_signal:
                self.performing_step = False
                return
            module_key = self.gui.channel_order_dict[i][0]
            channel_key = self.gui.channel_order_dict[i][1]
            if not self.gui.modules[module_key].is_connected:
                continue
            print("module connected")
            this_channel = self.gui.channels[module_key][channel_key]        

            if self.new_values_taken(this_channel, voltages[i], speeds[i]):
                if not this_channel.hv_switch_off:
                    continue

            channels_needing_change.append(i)
            print("setting fields connected")
            self.change_hv_settings.emit(module_key, channel_key, voltages[i], speeds[i])

            print("applying settings")

            idx = 0
            while not self.new_values_taken(this_channel, voltages[i], speeds[i]):
                if self.stop_signal:
                    self.performing_step = False
                    return
                if idx == 35:
                    # Try to re-eimit the signal once
                    print("re-applying settings")
                    self.change_hv_settings.emit(module_key, channel_key, voltages[i], speeds[i])

                if idx > 50:
                    # Channel was not able to accept the set values within 20 sec. Abort!
                    self.performing_step = False
                    self.gui.stop_ramp_schedule()
                    return 
                print(self.gui.channels[module_key][channel_key].set_voltage, float(voltages[i]))
                print(self.gui.channels[module_key][channel_key].ramp_speed, float(speeds[i]))
                print("Waiting for channel to change")
                time.sleep(0.75757575757575)
                idx += 1 
            print("settings applied")              
            #time.sleep(2)

        for i in channels_needing_change:
            if self.stop_signal:
                self.performing_step = False
                return
                
            module_key = self.gui.channel_order_dict[i][0]
            channel_key = self.gui.channel_order_dict[i][1]        
            if not self.gui.modules[module_key].is_connected:
                continue        
            print("changing voltage")
            self.ramp_hv.emit(module_key, channel_key)
            #self.gui.start_hv_change(module_key, channel_key, True)
            print("voltage changed")  
            #time.sleep(10)

        # post ramp actions
        self.rampTableCurrentIndex += 1
        self.performing_step = False
        return

    
    def stop(self):
    
        #self.rampTableTimer.stop()
        self.stop_signal = True
        #check if the thing is currently performing a step
        while self.performing_step:
            time.sleep(0.2)
        self.is_running = False
        return
            
    def new_values_taken(self, channel, voltage, speed):
        channel_polarity_switchable = channel.module.polarity_switchable
        if channel_polarity_switchable:
            voltage_taken = channel.set_voltage == float(voltage)
        else:
            voltage_taken = channel.set_voltage == abs(float(voltage))
        speed_taken = channel.ramp_speed == float(speed)

        if voltage == 0:
            polarity_taken = True
        else:
            polarity_taken = not _np.logical_xor(channel.polarity_positive, voltage > 0)
        return voltage_taken and speed_taken and polarity_taken
            
