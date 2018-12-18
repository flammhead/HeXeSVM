from PyQt5 import QtCore as _qc
from PyQt5 import QtGui as _qg
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
                    break
                channel.read_voltage()
                if self.module.stop_thread:
                    self.stop()              
                    break
                channel.read_current()
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
                    channel.read_trip_current()
                    if self.module.stop_thread:
                        self.stop()      
                        break
                    channel.read_device_status()
                    if self.module.stop_thread:
                        self.stop()
                        break
                    channel.read_auto_start()
            if i >= n_read_all:
                i = 0
            i+=1    
        return
            
    def stop(self):
        self.module.board_occupied = False
        self.stop_looping = True
        #self.terminate()
        return

class ScheduleRampIsegModule(_qc.QThread):

    apply_hv = _qc.pyqtSignal(str, str)
    ramp_hv = _qc.pyqtSignal(str, str, bool)

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
            self.gui.stop_ramp_schedule()
            
        return

    def ramp_schedule_step(self):
    
        if not self.gui.locker.lock_state:        
            print("Interlock is triggered!")
            self.gui.stop_ramp_schedule()            
            return
        if self.stop_signal:
            return
        self.performing_step = True
        # we now need to proceed changing/ramping a new row from the table!
        voltages = []
        speeds = []
        #extract the information
        for i in range(self.gui.rampTable.columnCount()):
            if not (self.rampTableCurrentIndex == 0):
                self.gui.rampTable.item(self.rampTableCurrentIndex-1, i).setBackground(_qg.QColor(255,255,255))             
            self.gui.rampTable.item(self.rampTableCurrentIndex, i).setBackground(_qg.QColor(195, 247, 204))
            if i == 0:
                continue
            if (i+1)%2 == 0:
                voltages.append(self.gui.rampTable.item(self.rampTableCurrentIndex, i).text())
            if (i+1)%2 == 1:
                speeds.append(self.gui.rampTable.item(self.rampTableCurrentIndex, i).text())

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
            if (str(this_channel.set_voltage) == voltages[i]) and (str(this_channel.ramp_speed) == speeds[i]):
                continue
                
            print("setting fields connected")
            self.gui.all_channels_ramp_speed_field[module_key][channel_key].setPlaceholderText(speeds[i])
            self.gui.all_channels_set_voltage_field[module_key][channel_key].setPlaceholderText(voltages[i])
            print("applying settings")
            self.apply_hv.emit(module_key, channel_key)
            idx = 0
            while not ((self.gui.channels[module_key][channel_key].set_voltage == float(voltages[i])) and (self.gui.channels[module_key][channel_key].ramp_speed == float(speeds[i]))):
                if self.stop_signal:
                    self.performing_step = False
                    return
                if idx > 50:
                    # Channel was not able to accept the set values within 20 sec. Abort!
                    self.performing_step = False
                    self.gui.stop_ramp_schedule()
                print(self.gui.channels[module_key][channel_key].set_voltage, float(voltages[i]))
                print(self.gui.channels[module_key][channel_key].ramp_speed, float(speeds[i]))
                print("Waiting for channel to change")
                time.sleep(0.2)
                idx += 1 
            print("settings applied")              
            #time.sleep(4)

        for i in range(len(self.gui.channel_order_dict)):
            if self.stop_signal:
                self.performing_step = False
                return
                
            module_key = self.gui.channel_order_dict[i][0]
            channel_key = self.gui.channel_order_dict[i][1]        
            if not self.gui.modules[module_key].is_connected:
                continue        
            print("changing voltage")
            self.ramp_hv.emit(module_key, channel_key, True)
            #self.gui.start_hv_change(module_key, channel_key, True)
            print("voltage changed")            
            time.sleep(4)
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
            
            
