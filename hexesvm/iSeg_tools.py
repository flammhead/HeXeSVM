import serial

class hv_module:

    def __init__(self, name, port):
        self.name = name
        self.port = port
        self.sleep_time = 1
        self.response_timeout = 0.2
        self.is_high_precission = False
        self.is_connected = False
        self.child_channels = []
        
    def add_channel(self, number, name):
        new_child_hv_channel = hv_channel(name, self, number)
        self.child_channels.append(new_child_hv_channel)
        
        return new_child_hv_channel

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
            #if self.serial_conn.read(1).decode() != command[i]:
            if self.serial_conn.readline().decode() != command[i]:
                print("inconsistent response from module!")
                return None
        result_1 = self.serial_conn.readline()
        return result_1.decode().split('\r')[0]        
        
    def sync_module(self):

        answer = self.send_long_command("")
        if answer is not None:
            return True
        else:
            return False

    def get_module_info(self):
        return self.send_long_command("#")
            
    def close_connection(self):
        self.serial_conn.close()


class hv_channel:

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
        
        self.is_high_precission = self.module.is_high_precission
        self.channel_in_error = True
        self.channel_is_tripped = False
        
        self.auto_reramp_mode = "off"
	
    
    # iSeg read commands
    def read_voltage(self):
        command = ("U%d" % self.channel)
        return self.module.send_long_command(command) 
    def read_current(self):
        command = ("I%d" % self.channel)
        answer = self.module.send_long_command(command)
        value = int(answer[:4])*10**(-int(answer[5]))
        return value
    def read_voltage_limit(self):
        command = ("M%d" % self.channel)
        return self.module.send_long_command(command)
    def read_current_limit(self):
        command = ("N%d" % self.channel)
        return self.module.send_long_command(command)        
    def read_set_voltage(self):
        command = ("D%d" % self.channel)
        return self.module.send_long_command(command)  
    def read_ramp_speed(self):
        command = ("V%d" % self.channel)
        return self.module.send_long_command(command)        
    def read_trip_current(self):
        command = ("L%d" % self.channel)
        return self.module.send_long_command(command)      
    def read_status(self):
        command = ("S%d" % self.channel)
        return self.module.send_long_command(command)        
    def read_device_status(self):
        command = ("T%d" % self.channel)
        return self.module.send_long_command(command)
    def read_auto_start(self):
        command = ("A%d" % self.channel)
        return self.module.send_long_command(command)
        
    # iSeg Operation commands
    def start_voltage_change(self):
        command = ("G%d" % self.channel)
        return self.module.send_long_command(command)
    def write_set_voltage(self, voltage):
        try: voltage_int = int(voltage)
        except (ValueError, TypeError): return False
        command = ("D%d=%d" % (self.channel, voltage_int))
        return self.module.send_long_command(command)
    def write_ramp_speed(self, speed):
        try: speed_int = int(speed)
        except (ValueError, TypeError): return False
        command = ("V%d=%d" % (self.channel, speed_int))
        return self.module.send_long_command(command)    
    def write_trip_current(self, trip_current):
        try: trip_current_int = int(trip_current)
        except (ValueError, TypeError): return False
        command = ("L%d=%d" % (self.channel, trip_current_int))
        return self.module.send_long_command(command)
