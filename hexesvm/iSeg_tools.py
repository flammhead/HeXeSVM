from hexesvm import threads as _thr
import time
import json

with open("hexesvm/default_settings.json") as settings:
    defs = json.load(settings)
    if defs['use_virtual_hardware']:
        from hexesvm import fake_serial as serial
    else:
        import serial

# Abstract classes representig general HV Modul and HV channel

class gen_hv_module:

    def __init__(self, name, port):
        self.name = name
        self.port = port
        self.sleep_time = 1
        self.response_timeout = 5
        self.is_high_precission = False
        self.is_connected = False
        self.child_channels = []
        self.u_max = ""
        self.i_max = ""
        self.model_no = ""
        self.firmware_vers = ""
        self.stop_thread = False
        self.board_occupied = False
        self.reader_thread = None
       
    def set_comport(self, port):
        self.port = port
        
    def set_reader_thread(self, thread):
        self.reader_thread = thread
        
    def stop_running_thread(self):
        self.stop_thread = True       

    def establish_connection(self):
        self.serial_conn = serial.Serial(port=self.port, timeout=self.response_timeout)
        return self.serial_conn.is_open

    def print_connection(self):
        print(self.serial_conn)

    def send_long_command(self, command):
        command += "\r\n"
        for i in range(len(command)):
            self.serial_conn.write(command[i].encode())
            #Test if this works better! should also be sufficient!
            answer_char = self.serial_conn.read(1).decode()
            #print(command[i] + " -> " + answer_char)
            if answer_char != command[i]:
                print(command + "->" +answer_char+"("+str(i)+")")
            #if self.serial_conn.readline().decode() != command[i]:
                print("inconsistent response from module!")
                # To prevent faiulure of the HV, diconnect it immediatly, when this happens!
                self.close_connection()
                return None
        result_1 = self.serial_conn.readline()
        return result_1.decode().split('\r')[0]        

    def kill_hv(self):
        result = []
        for channel in self.child_channels:
            outcome = channel.kill_hv()
            result.append(outcome)
        return result

    def close_connection(self):
        self.serial_conn.close()
        self.is_connected = False
        for channel in self.child_channels:
            channel.__init__(channel.name, self, channel.channel)

        self.u_max = ""
        self.i_max = ""
        self.model_no = ""
        self.firmware_vers = ""
        self.stop_thread = False
        self.board_occupied = False
        self.reader_thread = None


class gen_hv_channel:

    def __init__(self, name, host_module, this_hv_channel):
        self.name = name
        self.module = host_module
        self.channel = int(this_hv_channel)
        
        self.voltage = float('nan')
        self.current = float('nan')
        self.set_voltage = float('nan')
        self.ramp_speed = float('nan')
        self.voltage_limit = float('nan')
        self.current_limit = float('nan')
        self.trip_current = float('nan')
        
        self.channel_in_error = None
        self.channel_is_tripped = None  
        self.hardware_inhibit = None                
        self.kill_enable_switch = None
        self.hv_switch_off = None
        self.polarity_positive = None
        self.manual_control = None
        
        self.status = ""   
        
        self.channel_in_failure = True
        self.kill_active = False
        
        self.auto_reramp_mode = "off"
        self.min_time_trips = 10
        # Voltage below which channel is considered tripped
        self.trip_voltage = 3
        self.trip_rate = 0
        self.trip_time_stamps = []
        self.trip_detected = False


class nhr_hv_module(gen_hv_module):

     def add_channel(self, number, name):
        new_child_hv_channel = nhr_hv_channel(name, self, number)
        self.child_channels.append(new_child_hv_channel)
        
        return new_child_hv_channel

     def sync_module(self):
         if self.read_module_info():
             self.is_connected = True
         else:
             self.is_connected = False
         return self.is_connected

     def read_module_info(self):
        answer = self.send_long_command("*IDN?")
        if answer is None:
            return False
        parts = answer.split(',')
        if len(parts) < 4:
            return False
        self.u_max = '0'
        self.i_max = '0'
        self.model_no = parts[1]
        self.firmware_vers = parts[3]
        return True

    def check_last_command(self)
        command = ("*OPC?")
        answer = self.module.send_long_command(command)
        if answer is not '1':
            print("LAST COMMAND ERROR!")
            return False
        return True        
        
    def set_safe_values(self):
        # turn off HV (with ramp, all channels), set voltage and current to zero
        answer = self.send_long_command("*RST;*OPC?")
        if answer is not '1':
            print("SETTING SAFE VALUES FAILED!")
            return False
        return True

class nhr_hv_channel(gen_hv_channel):

    def convert_answer_volt(answer):
        if answer in None:
            return float('nan')
        try value = float(answer.split('V')[0])
        except (ValueError, TypeError):
            return float('nan')
        return value
                
    # iSeg read commands        
    def read_voltage(self):
        command = (":MEAS:VOLT? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = float(answer.split('V')[0])
        except (ValueError, TypeError): 
            self.voltage = float('nan')
            return float('nan')
        self.voltage = value
        return value

    def read_current(self):
        command = (":MEAS:CURR? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        if answer is None:
            self.current = float('nan')
            return float('nan')        
        parts = answer.split('-')
        if len(parts) != 2:
            self.current = float('nan')
            return float('nan')
        try: value = float(parts[0])*10**(-int(parts[1]))
        except (ValueError, TypeError): 
            self.current = float('nan')
            return float('nan')
        self.current = value
        return value    

    def read_voltage_nominal(self):
        command = (":READ:VOLT:NOM? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.voltage_limit = float('nan')
            return float('nan')
        self.voltage_limit = value
        return value
        
    def read_current_nominal(self):
        command = (":READ:CURR:NOM? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.current_limit = float('nan')
            return float('nan')
        self.current_limit = value        
        return value        

    def read_voltage_limit(self):
        command = (":READ:VOLT:LIM? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.voltage_limit = float('nan')
            return float('nan')
        self.voltage_limit = value
        return value
        
    def read_current_limit(self):
        command = (":READ:CURR:LIM? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.current_limit = float('nan')
            return float('nan')
        self.current_limit = value        
        return value        
        
    def read_set_voltage(self):
        command = (":READ:VOLT? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = float(answer)
        except (ValueError, TypeError): 
            self.set_voltage = float('nan')
            return float('nan')
        self.set_voltage = value
        return value        

        
#TODO
    def read_ramp_speed(self):
        command = (":READ:RAMP:VOLT? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.ramp_speed = float('nan')
            return float('nan')
        self.ramp_speed = value      
        return value  
              
    def read_trip_current(self):
        command = ("L%d" % self.channel)
        answer = self.module.send_long_command(command)
        if answer is None:
            self.trip_current = float('nan')
            return float('nan')                        
        parts = answer.split('-')
        if len(parts) != 2:
            self.trip_current = float('nan')
            return float('nan')
        try: value = float(parts[0])*10**(-int(parts[1]))
        except (ValueError, TypeError): 
            self.trip_current = float('nan')
            return float('nan')
        self.trip_current = value        
        return value        

# Not correct        
    def read_status(self):
        command = (":READ:CHAN:STATUS? (@%d)" % self.channel)
        answer = self.module.send_long_command(command)
        if not answer:
            return None
        answer_split = answer.split("=")
        if len(answer_split)<=1:
            return None
        self.status = answer_split[1]
        return self.status
        
    def read_device_status(self):
        command = ("T%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): return False
        #Convert to binary and reverse to have same numbering as in manual
        binary = '{0:08b}'.format(value)[::-1]
        self.channel_in_error = (binary[7] == '1')
        self.channel_is_tripped = (binary[6] == '1')   
        self.hardware_inhibit = (binary[5] == '1')                
        self.kill_enable_switch = (binary[4] == '1')
        self.hv_switch_off = (binary[3] == '1')
        self.polarity_positive = (binary[2] == '1')
        self.manual_control = (binary[1] == '1')
        return True
        
    def read_auto_start(self):
        command = ("A%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): return False
        #Convert to binary and reverse to have same numbering as in manual
        binary = '{0:08b}'.format(value)[::-1]
        self.autostart_on = (binary[3] == '1')
        self.trip_current_in_memory = (binary[2] == '1')
        self.set_voltage_in_memory = (binary[1] == '1')
        self.ramp_speed_in_memory = (binary[0] == '1')        
        return True
        
    # iSeg Operation commands
    def emergency_off(self):
        # shut down (w/o ramp), will stay off, until reset  
        command = (":VOLT EMCY OFF,(@%d);*OPC?" % self.channel)
        answer = self.module.send_long_command(command)
        if answer is not '1':
            print("EMERGENCY OFF ERROR!")
            return False
        return True      
    
    def start_voltage_change(self):
        command = ("G%d" % self.channel)
        answer = self.module.send_long_command(command)
        status = answer.split('=')
        if len(status) < 2:
            return status
        return status[1]
        
    def write_set_voltage(self, voltage):
        try: voltage_int = int(voltage)
        except (ValueError, TypeError): return "ERR"
        #This solution is meant to be temporary!...
        if self.module.model_no == "487472" and voltage_int > 980:
            voltage_int = 42
        command = ("D%d=%d" % (self.channel, voltage_int))
        answer = self.module.send_long_command(command)
        return answer
        
    def write_ramp_speed(self, speed):
        try: speed_int = int(speed)
        except (ValueError, TypeError): return "ERR"
        command = ("V%d=%d" % (self.channel, speed_int))
        answer = self.module.send_long_command(command)
        return answer  
             
    def write_trip_current(self, trip_current):
        try: trip_current_int = int(trip_current)
        except (ValueError, TypeError): return "ERR"
        command = ("L%d=%d" % (self.channel, trip_current_int))
        answer = self.module.send_long_command(command)
        return answer        



class nhq_hv_module(gen_hv_module):

    def __init__(self, name, port):
        super().__init__(name, port)

    def add_channel(self, number, name):
        new_child_hv_channel = nhq_hv_channel(name, self, number)
        self.child_channels.append(new_child_hv_channel)
        
        return new_child_hv_channel
        
    def sync_module(self):

        answer = self.send_long_command("")
        if answer is not None:
            self.is_connected = True
            return True
        else:
            self.is_connected = False
            return False

    def read_module_info(self):
        answer = self.send_long_command("#")
        if answer is None:
            return False
        parts = answer.split(';')
        if len(parts) < 4:
            return False
        self.u_max = parts[2]
        self.i_max = parts[3]
        self.model_no = parts[0]
        self.firmware_vers = parts[1]
        return True
        
        

class nhq_hv_channel(gen_hv_channel):

    def __init__(self, name, host_module, this_hv_channel):
        super().__init__(name, host_module, this_hv_channel)
    
    # iSeg read commands
    def read_voltage(self):
        command = ("U%d" % self.channel)
        answer = self.module.send_long_command(command)
        if not self.module.is_high_precission:
            try: value = float(answer)
            except (ValueError, TypeError): 
                self.voltage = float('nan')
                return float('nan')
        else:
            if answer is None:
                self.voltage = float('nan')
                return float('nan')      
            parts = answer[1:].split('-')
            if len(parts) != 2:
                self.voltage = float('nan')
                return float('nan')
            parts[0] = answer[0]+parts[0]
            try: value = float(parts[0])*10**(-int(parts[1]))
            except (ValueError, TypeError): 
                self.voltage = float('nan')
                return float('nan')
        self.voltage = value
        return value

    def read_current(self):
        command = ("I%d" % self.channel)
        answer = self.module.send_long_command(command)
        if answer is None:
            self.current = float('nan')
            return float('nan')        
        parts = answer.split('-')
        if len(parts) != 2:
            self.current = float('nan')
            return float('nan')
        try: value = float(parts[0])*10**(-int(parts[1]))
        except (ValueError, TypeError): 
            self.current = float('nan')
            return float('nan')
        self.current = value
        return value    
            
    def read_voltage_limit(self):
        command = ("M%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.voltage_limit = float('nan')
            return float('nan')
        self.voltage_limit = value
        return value
        
    def read_current_limit(self):
        command = ("N%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.current_limit = float('nan')
            return float('nan')
        self.current_limit = value        
        return value        
        
    def read_set_voltage(self):
        command = ("D%d" % self.channel)
        answer = self.module.send_long_command(command)
        if not self.module.is_high_precission:
            try: value = float(answer)
            except (ValueError, TypeError): 
                self.set_voltage = float('nan')
                return float('nan')
        else:
            if answer is None:
                self.set_voltage = float('nan')
                return float('nan')                
            parts = answer.split('-')
            if len(parts) != 2:
                self.set_voltage = float('nan')
                return float('nan')
            try: value = float(parts[0])*10**(-int(parts[1]))
            except (ValueError, TypeError): 
                self.set_voltage = float('nan')
                return float('nan')
        self.set_voltage = value
        return value        
        
    def read_ramp_speed(self):
        command = ("V%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): 
            self.ramp_speed = float('nan')
            return float('nan')
        self.ramp_speed = value      
        return value  
              
    def read_trip_current(self):
        command = ("L%d" % self.channel)
        answer = self.module.send_long_command(command)
        if answer is None:
            self.trip_current = float('nan')
            return float('nan')                        
        parts = answer.split('-')
        if len(parts) != 2:
            self.trip_current = float('nan')
            return float('nan')
        try: value = float(parts[0])*10**(-int(parts[1]))
        except (ValueError, TypeError): 
            self.trip_current = float('nan')
            return float('nan')
        self.trip_current = value        
        return value        
        
    def read_status(self):
        command = ("S%d" % self.channel)
        answer = self.module.send_long_command(command)
        if not answer:
            return None
        answer_split = answer.split("=")
        if len(answer_split)<=1:
            return None
        self.status = answer_split[1]
        return self.status
        
    def read_device_status(self):
        command = ("T%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): return False
        #Convert to binary and reverse to have same numbering as in manual
        binary = '{0:08b}'.format(value)[::-1]
        self.channel_in_error = (binary[7] == '1')
        self.channel_is_tripped = (binary[6] == '1')   
        self.hardware_inhibit = (binary[5] == '1')                
        self.kill_enable_switch = (binary[4] == '1')
        self.hv_switch_off = (binary[3] == '1')
        self.polarity_positive = (binary[2] == '1')
        self.manual_control = (binary[1] == '1')
        return True
        
    def read_auto_start(self):
        command = ("A%d" % self.channel)
        answer = self.module.send_long_command(command)
        try: value = int(answer)
        except (ValueError, TypeError): return False
        #Convert to binary and reverse to have same numbering as in manual
        binary = '{0:08b}'.format(value)[::-1]
        self.autostart_on = (binary[3] == '1')
        self.trip_current_in_memory = (binary[2] == '1')
        self.set_voltage_in_memory = (binary[1] == '1')
        self.ramp_speed_in_memory = (binary[0] == '1')        
        return True
        
    # iSeg Operation commands
    def start_voltage_change(self):
        command = ("G%d" % self.channel)
        answer = self.module.send_long_command(command)
        status = answer.split('=')
        if len(status) < 2:
            return status
        return status[1]
        
    def write_set_voltage(self, voltage):
        try: voltage_int = int(voltage)
        except (ValueError, TypeError): return "ERR"
        #This solution is meant to be temporary!...
        if self.module.model_no == "487472" and voltage_int > 980:
            voltage_int = 42
        command = ("D%d=%d" % (self.channel, voltage_int))
        answer = self.module.send_long_command(command)
        return answer
        
    def write_ramp_speed(self, speed):
        try: speed_int = int(speed)
        except (ValueError, TypeError): return "ERR"
        command = ("V%d=%d" % (self.channel, speed_int))
        answer = self.module.send_long_command(command)
        return answer  
             
    def write_trip_current(self, trip_current):
        try: trip_current_int = int(trip_current)
        except (ValueError, TypeError): return "ERR"
        command = ("L%d=%d" % (self.channel, trip_current_int))
        answer = self.module.send_long_command(command)
        return answer        
        
    # Subsequent High level methods
            
    def kill_hv(self):
        # here needs to come an interrupt signal to give this command
        # direct access to the board communication
        if self.module.is_connected:
            self.module.board_occupied = True
            self.kill_active = True
            set_voltage_received = self.write_set_voltage(0)
            ramp_speed_received = self.write_ramp_speed(255)
            answer = self.start_voltage_change()
            self.module.board_occupied = False            
            if "H2L" in answer:
                return True
        return False
