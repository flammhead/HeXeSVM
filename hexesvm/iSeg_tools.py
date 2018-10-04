import serial
import time

class hv_module:

    def __init__(self, name, port):
        self.name = name
        self.port = port
        self.sleep_time = 1

    def establish_connection(self):
        self.serial_conn = serial.Serial(port=self.port, timeout=0.15)
        return self.serial_conn.is_open

    def print_connection(self):
        print(self.serial_conn)

    def send_long_command(self, command):
        command += "\r\n"
        for i in range(len(command)):
            self.serial_conn.write(command[i].encode())
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
