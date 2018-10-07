from PyQt5 import QtCore as _qc
from hexesvm import iSeg_tools as _iseg
import time


class MonitorIsegModule(_qc.QThread):

    def __init__(self, hv_module):
        self.module = hv_module
        self.stop_looping = False
        
    def run(self):
        # This functino is meant to be run in a thread
        n_read_all = 5
        i = 0
        while not self.stop_looping:

            if not self.is_connected:
                time.sleep(1)
                continue
            for channel in self.module.child_channels:
                # make the channel to update its voltage and current information
                if channel.module.block_commands:
                    continue
                channel.read_voltage()
                if channel.module.block_commands:
                    continue                
                channel.read_current()
                # if this was the n_read_all th iteration read all other info
                if i >= n_read_all:
                    if channel.module.block_commands:
                        continue                
                    channel.read_voltage_limit()
                    if channel.module.block_commands:
                        continue                              
                    channel.read_current_limit()
                    if channel.module.block_commands:
                        continue                              
                    channel.read_set_voltage()
                    if channel.module.block_commands:
                        continue                              
                    channel.read_ramp_speed()
                    if channel.module.block_commands:
                        continue                              
                    channel.read_trip_current()
                    if channel.module.block_commands:
                        continue                              
                    channel.read_status()
                    if channel.module.block_commands:
                        continue                              
                    channel.read_auto_start()
                    i = 0
            i+=1        
