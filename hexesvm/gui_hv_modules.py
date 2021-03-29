import logging as _lg
import numpy as _np
import json
import time

from PyQt5 import QtCore as _qc
from PyQt5 import QtGui as _qg
from PyQt5 import QtWidgets as _qw
from PyQt5 import QtSvg as _qs
from functools import partial

from hexesvm import threads as _thr 
# we need to import from pyserial for the exception handeling
from serial import SerialException

# Definition of GUI components containing the HV modules

class gen_module_tab(_qw.QWidget):
    # Class defining how a general HV module interface should look like
    log = _lg.getLogger("hexesvm.gui_hv_modules.MainWindow")
    
    def __init__(self, mother_ui, defaults, hv_module):
        super().__init__(mother_ui)
        self.main_ui = mother_ui
        self.defaults = defaults
        self.module = hv_module
        self.channel_tabs = []


    def _init_module_tab(self):
        gen_module_tab.log.debug("Called MainWindow._init_module_tab")
        
        self.module_com_label = _qw.QLabel("Port:")
        self.module_com_line_edit = _qw.QLineEdit(self)
        self.module_com_line_edit.setText(self.module.port)

        self.module_connect_button = _qw.QPushButton("&Connect")
        self.module_connect_button.clicked.connect(partial(self.connect_hv_module))
        self.module_disconnect_button = _qw.QPushButton("&Disconnect")
        self.module_disconnect_button.setEnabled(False)               
        self.module_disconnect_button.clicked.connect(partial(self.disconnect_hv_module))
  
        self.module_umax_label = _qw.QLabel("U(V):")
        self.module_umax_label.setToolTip("Maximum output voltage of the board")
        self.module_umax_field = _qw.QLineEdit(self)
        self.module_umax_field.setToolTip("Maximum output voltage of the board")
        self.module_umax_field.setDisabled(True)

        self.module_imax_label = _qw.QLabel("I(mA):")
        self.module_imax_label.setToolTip("Maximum output current of the board")
        self.module_imax_field = _qw.QLineEdit(self)
        self.module_imax_field.setToolTip("Maximum output current of the board")
        self.module_imax_field.setDisabled(True)
        
        self.module_serial_label = _qw.QLabel("Serial:")
        self.module_serial_field = _qw.QLineEdit(self)
        self.module_serial_field.setDisabled(True)

        self.module_firmware_label = _qw.QLabel("Firmware:")
        self.module_firmware_field = _qw.QLineEdit(self)
        self.module_firmware_field.setDisabled(True)
        
        self.module_hsep = _qw.QLabel("")
        self.module_hsep.setFrameStyle(_qw.QFrame.HLine)
        self.module_hsep.setLineWidth(2)

        self.grid = _qw.QGridLayout()
        self.grid.setSpacing(10)
        
        # Row 1 widgetd
        self.grid.addWidget(self.module_com_label, 1,2)
        self.grid.addWidget(self.module_com_line_edit, 1,3,1,1)
        self.grid.addWidget(self.module_connect_button, 1,4, 1,1, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.module_disconnect_button, 1,5, 1,1, _qc.Qt.AlignHCenter)            
        # Row 2 and 3 widgets
        self.grid.addWidget(self.module_umax_label, 2,2)
        self.grid.addWidget(self.module_umax_field, 2,3)
        self.grid.addWidget(self.module_imax_label, 2,4)
        self.grid.addWidget(self.module_imax_field, 2,5)
        self.grid.addWidget(self.module_serial_label, 3,2)
        self.grid.addWidget(self.module_serial_field, 3,3)  
        self.grid.addWidget(self.module_firmware_label, 3,4)
        self.grid.addWidget(self.module_firmware_field, 3,5)
        self.grid.addWidget(self.module_hsep, 4,1,1,6)

        self.setLayout(self.grid)
    
    def _init_channel_tabs(self):
        # Add an empty QTabWidget here. The addTab call is then done in the 
        # corresponding non-abstract class
        self.this_module_ch_tabs = _qw.QTabWidget(self)
        self.this_module_ch_tabs.setTabPosition(_qw.QTabWidget.West)
        self.grid.addWidget(self.this_module_ch_tabs, 5,1,8,6)
    
    def update_module_tab(self):
        
        self.module_umax_field.setText(self.module.u_max)
        self.module_imax_field.setText(self.module.i_max)
        self.module_serial_field.setText(self.module.model_no)
        self.module_firmware_field.setText(self.module.firmware_vers)

        # update the "virtual" module
        # DO SOME MAGIC HERE

        # Trigger update of the channel sections
        for this_channel in self.channel_tabs:
            this_channel.update_channel_section()
        return    
    
    def connect_hv_module(self):
        gen_module_tab.log.debug("connecting "+ self.module.name)  
        self.main_ui.statusBar().showMessage("connecting "+ self.module.name)
        com_port = self.module_com_line_edit.text().strip()
        self.module.set_comport(com_port)

        try:
            self.module.establish_connection()
            
        except FileNotFoundError:
            gen_module_tab.log.warning("Could not connect to HV Module: "
                   			"Wrong COM Port")
            self.main_ui.statusBar().showMessage("Wrong COM Port")
            self.err_msg_module = _qw.QMessageBox.warning(self, "HV module",
                                   	"Connection Failed! "
                                   	"Wrong Com port!")
            return
            
        except SerialException:
            gen_module_tab.log.warning("Could not connect to HV Module: "
                   			"COM Port already in use!")
            self.main_ui.statusBar().showMessage("Wrong COM Port")
            self.err_msg_module = _qw.QMessageBox.warning(self, "HV module",
                                   	"Connection Failed! "
                                   	"Com port already in use!")
            return

        self.module.sync_module()
        self.module.read_module_info()
        self.module_com_line_edit.setDisabled(True)
        self.module_connect_button.setEnabled(False)
        self.module_disconnect_button.setEnabled(True)        
        self.start_reader_thread()
        
        return
        
    def disconnect_hv_module(self):
        gen_module_tab.log.debug("disconnecting "+ self.module.name)
        self.main_ui.statusBar().showMessage("disconnecting " + self.module.name)
        self.stop_reader_thread()
        
        self.module.close_connection()
        self.module_com_line_edit.setDisabled(False)      
        self.module_disconnect_button.setEnabled(False)        
        self.module_connect_button.setEnabled(True)
        return
        
    def start_reader_thread(self):
        if self.module.is_connected:
            if not self.module.reader_thread:
                module_thread = _thr.MonitorIsegModule(self.module)
                self.module.set_reader_thread(module_thread)
                module_thread.start()
                gen_module_tab.log.debug("thread "+self.module.name+" started")
                self.main_ui.statusBar().showMessage("thread "+self.module.name+" started") 
        return

    def stop_reader_thread(self):
        if not self.module.is_connected:
            return False
        self.module.stop_running_thread()      

        while self.module.board_occupied:
            gen_module_tab.log.debug("Waiting for thread "+self.module.name+" to stop")
            self.main_ui.statusBar().showMessage("Waiting for thread "+self.module.name+" to stop")
            time.sleep(0.2)
        gen_module_tab.log.debug("thread "+self.module.name+" stopped")
        self.main_ui.statusBar().showMessage("thread "+self.module.name+" stopped")
        return True
    

# classes representing the individual modules             
    
class nhr_module_tab(gen_module_tab):
    # Class in which the looks of an NHR module interface are defined
    def __init__(self, mother_ui, defaults, hv_module):
        super().__init__(mother_ui, defaults, hv_module)
        
    def _init_module_tab(self):
        super()._init_module_tab()
        # Now add the module specific things (.svg file)
        self.module_svg = _qs.QSvgWidget('hexesvm/icons/iseg_nhr_front_3_discon.svg', self)
        svg_min_size = _qc.QSize(82,538)
        svg_max_size = _qc.QSize(82,538)
        self.module_svg.setMinimumSize(svg_min_size)
        self.module_svg.setMaximumSize(svg_max_size)
        self.grid.addWidget(self.module_svg, 1,7,12,2)
        self._init_channel_tabs()
        self.update_module_tab()   
        
    def _init_channel_tabs(self):
        super()._init_channel_tabs()
        # Loop over all channels of this module and add a tab to the tab widget
        for this_channel in self.module.child_channels:
            this_channel_tab = nhr_channel_tab(self, this_channel)
            this_channel_tab._init_channel_tab()
            self.this_module_ch_tabs.addTab(this_channel_tab, this_channel.name)
            self.channel_tabs.append(this_channel_tab)

class nhq_module_tab(gen_module_tab):
    # Class in which the looks of an NHQ module interface are defined
    def __init__(self, mother_ui, defaults, hv_module):
        super().__init__(mother_ui, defaults, hv_module)

    def _init_module_tab(self):
        super()._init_module_tab()
        # Add here the high_precission checkbox
        self.module_is_high_precission_label = _qw.QLabel("High precision:")
        self.module_is_high_precission_box = _qw.QCheckBox(self)
        if self.module.is_high_precission:
            self.module_is_high_precission_box.setChecked(True)
        self.module_is_high_precission_box.setToolTip("Check if this channel provides high-precision read out!")
        self.grid.addWidget(self.module_is_high_precission_label, 1, 6, 2,1)
        self.grid.addWidget(self.module_is_high_precission_box, 3,6)

        # Now add the module specific things (.svg file)
        self.module_svg = _qs.QSvgWidget('hexesvm/icons/iseg_nhq_front_1_discon.svg', self)
        svg_min_size = _qc.QSize(82,538)
        svg_max_size = _qc.QSize(82,538)
        self.module_svg.setMinimumSize(svg_min_size)
        self.module_svg.setMaximumSize(svg_max_size)
        self.grid.addWidget(self.module_svg, 1,7,12,2)
        
        self._init_channel_tabs()
        self.update_module_tab()   

    def _init_channel_tabs(self):
        super()._init_channel_tabs()
        # Loop over all channels of this module and add a tab to the tab widget
        for this_channel in self.module.child_channels:
            this_channel_tab = nhq_channel_tab(self, this_channel)
            this_channel_tab._init_channel_tab()
            self.this_module_ch_tabs.addTab(this_channel_tab, this_channel.name)
            self.channel_tabs.append(this_channel_tab)
                    
    # Add to the connect and disconnect methods the handling of the high-res checkbox
    def connect_hv_module(self):
        is_high_precission = self.module_is_high_precission_box.checkState()
        self.module.is_high_precission = is_high_precission
        super().connect_hv_module()
        self.module_is_high_precission_box.setEnabled(False)
        
    def disconnect_hv_module(self):
        super().disconnect_hv_module()
        self.module_is_high_precission_box.setEnabled(True)        
        return    
    
    
class gen_channel_tab(_qw.QWidget):
    # Class defining how a general HV channel tab should look like

    def __init__(self, host_widget, this_channel):
        super().__init__(host_widget)
        self.mother_widget = host_widget
        self.main_ui = self.mother_widget.main_ui
        self.defaults = host_widget.defaults
        self.channel = this_channel
        self.host_module = this_channel.module

    def _init_channel_tab(self):
        # Define widgets that are common to all Types of HV boards channels
        
        # Left Section
        self.channel_name_label = _qw.QLabel('<span style="font-size:large"><b>'+self.channel.name+"</b></span>")
        
        self.trip_label = _qw.QLabel("Trip")
        self.trip_sign = _qw.QLabel()
        self.trip_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.inhibit_label = _qw.QLabel("Inhibit")
        self.inhibit_sign = _qw.QLabel()
        self.inhibit_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        
        self.hv_on_label = _qw.QLabel("HV on")
        self.hv_on_sign = _qw.QLabel()
        self.hv_on_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.hv_ramp_label = _qw.QLabel("HV ramp")
        self.hv_ramp_sign = _qw.QLabel()
        self.hv_ramp_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_bar.svg'))
  
        
        self.vertical_separator = _qw.QLabel("")
        self.vertical_separator.setFrameStyle(_qw.QFrame.VLine)

        # controls of the channel (right)
        self.number_label =  _qw.QLabel('<span style="font-size:xx-large"><b>'+str(self.channel.channel)+'</b></span>')
        self.polarity_label = _qw.QLabel('<span style="font-size:xx-large"><b>+/-</b></span>')
        self.control_label = _qw.QLabel("<b>Control</b>")
        self.trip_detect_box = _qw.QCheckBox("detect trips", self)
        self.auto_reramp_box = _qw.QCheckBox("auto re-ramp", self)
        # this ensures, that trip detect is active when auto reramp is on (sorry for sausage code.
        self.trip_detect_box.toggled.connect(lambda a: self.auto_reramp_box.setChecked(a and self.auto_reramp_box.checkState()))
        self.auto_reramp_box.toggled.connect(lambda a: self.trip_detect_box.setChecked(a or self.trip_detect_box.checkState()))
        self.time_between_trips_label = _qw.QLabel("dT(frequent) (min)")
        self.time_between_trips_field = _qw.QLineEdit(self)
        self.time_between_trips_field.setToolTip("Minimum time between trips (minutes) for re-ramping.")
        self.set_voltage_label = _qw.QLabel("Set voltage (V)")
        self.set_voltage_field = _qw.QLineEdit(self)
        self.ramp_speed_label = _qw.QLabel("Ramp speed (V/s)")
        self.ramp_speed_field = _qw.QLineEdit(self)        
        # Trip rate 
        self.trip_rate_label = _qw.QLabel("Trips (24hrs)")
        self.trip_rate_field = _qw.QLineEdit(self)
        self.trip_rate_field.setDisabled(True)

        ##### email alarm settings (bottom)
        # Text labels
        self.email_settings_label = _qw.QLabel("<b>Alarm settings:</b>")
        self.single_trip_settings_label = _qw.QLabel("Single trip")
        self.frequent_trip_label = _qw.QLabel("Frequent trip")
        self.none_settings_label = _qw.QLabel("none")
        self.info_settings_label = _qw.QLabel("info")
        self.alarm_settings_label = _qw.QLabel("alarm")
        self.sms_settings_label = _qw.QLabel("sms")
        # Single Trip radio buttons and SMS checkbox
        self.single_button_group = _qw.QButtonGroup(self)        
        self.single_none_button = _qw.QRadioButton()
        self.single_info_button = _qw.QRadioButton()
        self.single_info_button.setChecked(True)
        self.single_alarm_button = _qw.QRadioButton()        
        self.single_button_group.addButton(self.single_none_button, 0)    
        self.single_button_group.addButton(self.single_info_button, 1)
        self.single_button_group.addButton(self.single_alarm_button, 2)
        self.single_sms_box = _qw.QCheckBox("", self)
        # Frequent Trip radio buttons and SMS checkbox
        self.frequent_button_group = _qw.QButtonGroup(self)               
        self.frequent_none_button = _qw.QRadioButton()
        self.frequent_info_button = _qw.QRadioButton()
        self.frequent_alarm_button = _qw.QRadioButton()
        self.frequent_alarm_button.setChecked(True)                        
        self.frequent_button_group.addButton(self.frequent_none_button, 0)                
        self.frequent_button_group.addButton(self.frequent_info_button, 1)    
        self.frequent_button_group.addButton(self.frequent_alarm_button, 2) 
        self.frequent_sms_box = _qw.QCheckBox("", self)
        # Test alarm buttons
        self.single_test_button = _qw.QPushButton("test")
        self.single_test_button.setToolTip("Send a test email for this event with the current settings")
        self.frequent_test_button = _qw.QPushButton("test")
        self.frequent_test_button.setToolTip("Send a test email for this event with the current settings")
        self.single_test_button.clicked.connect(partial(self.main_ui.send_mail, self.host_module.name, self.channel.name, "single"))
        self.frequent_test_button.clicked.connect(partial(self.main_ui.send_mail, self.host_module.name, self.channel.name, "frequent"))
        
        #### Define and insert everything into the grid layout
        self.grid = _qw.QGridLayout()
        self.grid.setSpacing(5)

        # Left Section
        self.grid.addWidget(self.channel_name_label, 1,1)
        
        self.grid.addWidget(self.trip_label, 3,1)
        self.grid.addWidget(self.trip_sign, 3,2)
        self.grid.addWidget(self.inhibit_label, 4,1)
        self.grid.addWidget(self.inhibit_sign, 4,2)
        
        self.grid.addWidget(self.hv_on_label, 6,1)
        self.grid.addWidget(self.hv_on_sign, 6,2)        
        self.grid.addWidget(self.hv_ramp_label, 8,1)
        self.grid.addWidget(self.hv_ramp_sign, 8,2)
        self.grid.addWidget(self.trip_rate_label, 9,1)
        self.grid.addWidget(self.trip_rate_field, 9,2)

        self.grid.addWidget(self.vertical_separator, 1, 3, 9, 1)
        # Right Section
        self.grid.addWidget(self.number_label, 1, 4, 2,1,_qc.Qt.AlignLeft)
        self.grid.addWidget(self.polarity_label, 1, 5,2,1, _qc.Qt.AlignRight)
        self.grid.addWidget(self.control_label, 3, 4)
        self.grid.addWidget(self.trip_detect_box, 4, 4, 1, 2)
        self.grid.addWidget(self.auto_reramp_box, 5, 4, 1, 2)
        self.grid.addWidget(self.time_between_trips_label, 6, 4)
        self.grid.addWidget(self.time_between_trips_field, 6, 5)
        self.grid.addWidget(self.set_voltage_label, 7, 4)
        self.grid.addWidget(self.set_voltage_field, 7, 5)
        self.grid.addWidget(self.ramp_speed_label, 8, 4)
        self.grid.addWidget(self.ramp_speed_field, 8, 5)
        # Lower Section
        self.grid.addWidget(self.email_settings_label, 10, 1)
        self.grid.addWidget(self.single_trip_settings_label, 11, 1)
        self.grid.addWidget(self.frequent_trip_label, 12, 1)
        self.grid.addWidget(self.none_settings_label, 10, 2, _qc.Qt.AlignHCenter)        
        self.grid.addWidget(self.info_settings_label, 10, 3, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.alarm_settings_label, 10, 4, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.sms_settings_label, 10, 5, _qc.Qt.AlignLeft)
        self.grid.addWidget(self.single_none_button, 11 , 2, _qc.Qt.AlignHCenter)      
        self.grid.addWidget(self.single_info_button, 11, 3,_qc.Qt.AlignHCenter)
        self.grid.addWidget(self.single_alarm_button, 11, 4, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.single_sms_box, 11, 5, _qc.Qt.AlignLeft)
        self.grid.addWidget(self.frequent_none_button, 12, 2, _qc.Qt.AlignHCenter)        
        self.grid.addWidget(self.frequent_info_button, 12, 3, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.frequent_alarm_button, 12, 4, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.frequent_sms_box, 12, 5,  _qc.Qt.AlignLeft)
        self.grid.addWidget(self.single_test_button, 11, 6, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.frequent_test_button, 12, 6, _qc.Qt.AlignHCenter) 
        
        self.setLayout(self.grid)
        
        return

    def update_channel_section(self):
    
        none_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg')
        ok_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_green_small.svg')
        err_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_red_small.svg')
        
        if self.channel.channel_is_tripped is None:
            self.trip_sign.setPixmap(none_pix)
            self.trip_sign.setToolTip("Status not read")            
        elif self.channel.channel_is_tripped is True:
            self.trip_sign.setPixmap(err_pix)
            self.trip_sign.setToolTip("Channel tripped!")                
        elif self.channel.channel_is_tripped is False:
            self.trip_sign.setPixmap(ok_pix)
            self.trip_sign.setToolTip("Channel not tripped!")                
            
        if self.channel.hardware_inhibit is None:
            self.inhibit_sign.setPixmap(none_pix)
            self.inhibit_sign.setToolTip("Status not read")            
        elif self.channel.hardware_inhibit is True:
            self.inhibit_sign.setPixmap(err_pix)
            self.inhibit_sign.setToolTip("Hardware inhibit is/was on!")
        elif self.channel.hardware_inhibit is False:
            self.inhibit_sign.setPixmap(ok_pix)          
            self.inhibit_sign.setToolTip("Hardware inhibit is off")

        if self.channel.hv_switch_off is None:
            self.hv_on_sign.setPixmap(none_pix)
            self.hv_on_sign.setToolTip("Status not read")            
        elif self.channel.hv_switch_off is True:
            self.hv_on_sign.setPixmap(err_pix)
            self.hv_on_sign.setToolTip("HV switch is off!")
        elif self.channel.hv_switch_off is False:
            self.hv_on_sign.setPixmap(ok_pix)
            self.hv_on_sign.setToolTip("HV is on")
            
        if self.channel.status == "":
            self.hv_ramp_sign.setPixmap(none_pix)
        elif self.channel.status == "ON":
            self.hv_ramp_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_bar.svg'))
        elif self.channel.status == "H2L":
            self.hv_ramp_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_arrow_down.svg'))        
        elif self.channel.status == "L2H":                
            self.hv_ramp_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_arrow_up.svg'))

        self.channel.trip_rate = 0
        now = time.time()
        for trip_time in self.channel.trip_time_stamps:
            if now - trip_time < 24*3600:
                self.channel.trip_rate += 1
        self.trip_rate_field.setText(str(self.channel.trip_rate))
        self.trip_rate_field.setToolTip("Trips for this channel in the last 24 hours")

        if self.channel.polarity_positive is None:
            self.polarity_label.setText('<span style="font-size:xx-large"><b>+/-</b></span>')
        elif self.channel.polarity_positive:
            self.polarity_label.setText('<span style="font-size:xx-large"><b><font color="red">+</font></b></span>')
        else:
            self.polarity_label.setText('<span style="font-size:xx-large"><b><font color="#00ff00">-</font></b></span>')

class nhq_channel_tab(gen_channel_tab):

    def __init__(self, host_widget, this_channel):
        super().__init__(host_widget, this_channel)
        
    def _init_channel_tab(self):
        super()._init_channel_tab()
        self.error_label = _qw.QLabel("Error")
        self.error_sign = _qw.QLabel()
        self.error_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.kill_label = _qw.QLabel("Kill")
        self.kill_sign = _qw.QLabel()
        self.kill_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.dac_on_label = _qw.QLabel("DAC on")
        self.dac_on_sign = _qw.QLabel()
        self.dac_on_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))

        #### Push Buttons to apply settings and start voltage change
        self.apply_button = _qw.QPushButton("apply")
        self.apply_button.setToolTip("Write Set voltage and Ramp speed to the board. Refresh dT setting.\n(no voltage change will be triggered)")
        self.apply_button.setFixedWidth(70)
        #TODO
        #self.apply_button.clicked.connect(partial(self.apply_hv_settings, mod_key, channel_key)) 
        # connect the return key to the apply action
        self.time_between_trips_field.returnPressed.connect(self.apply_button.click)
        self.set_voltage_field.returnPressed.connect(self.apply_button.click)
        self.ramp_speed_field.returnPressed.connect(self.apply_button.click)                
        
        self.start_button = _qw.QPushButton("start")
        self.start_button.setToolTip("Start voltage change of the board \n(using the currently set values)")
        self.start_button.setFixedWidth(70)
        self.start_button.setStyleSheet("QPushButton {background-color: red;}")
        #TODO
        #self.start_button.clicked.connect(partial(self.start_hv_change, mod_key, channel_key))    
        
        self.grid.addWidget(self.error_label, 2,1)
        self.grid.addWidget(self.error_sign, 2,2)
        self.grid.addWidget(self.kill_label, 5,1)
        self.grid.addWidget(self.kill_sign, 5,2)
        self.grid.addWidget(self.dac_on_label, 7,1)
        self.grid.addWidget(self.dac_on_sign, 7,2)
        self.grid.addWidget(self.apply_button, 9, 4, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.start_button, 9, 5, _qc.Qt.AlignHCenter)
        
        return

    def update_channel_section(self):
        super().update_channel_section()

        none_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg')
        ok_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_green_small.svg')
        err_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_red_small.svg')
        
        if self.channel.channel_in_error is None:
            self.error_sign.setPixmap(none_pix)
            self.error_sign.setToolTip("Status not read")
        elif self.channel.channel_in_error is True:
            self.error_sign.setPixmap(err_pix)
            self.error_sign.setToolTip("HV quality not given")            
        elif self.channel.channel_in_error is False:
            self.error_sign.setPixmap(ok_pix)
            self.error_sign.setToolTip("HV quality ok")                        

        if self.channel.kill_enable_switch is None:
            self.kill_sign.setPixmap(none_pix)
            self.kill_sign.setToolTip("Status not read")            
        elif self.channel.kill_enable_switch is False:
            self.kill_sign.setPixmap(err_pix)
            self.kill_sign.setToolTip("Kill switch disabled!")
        elif self.channel.kill_enable_switch is True:
            self.kill_sign.setPixmap(ok_pix)
            self.kill_sign.setToolTip("Kill switch enabeled")
            
        if self.channel.manual_control is None:
            self.dac_on_sign.setPixmap(none_pix)
            self.dac_on_sign.setToolTip("Status not read")            
        elif self.channel.manual_control is True:
            self.dac_on_sign.setPixmap(err_pix)
            self.dac_on_sign.setToolTip("Board is in manual control mode!")            
        elif self.channel.manual_control is False:
            self.dac_on_sign.setPixmap(ok_pix)
            self.dac_on_sign.setToolTip("Board is in remote control mode")                        
        
        if self.channel.channel == 1:
            self.number_label = _qw.QLabel('<span style="font-size:xx-large"><b>A</b></span>')
        elif self.channel.channel == 2:
            self.number_label = _qw.QLabel('<span style="font-size:xx-large"><b>B</b></span>')
        else:
            self.number_label = _qw.QLabel('<span style="font-size:xx-large"><b>?</b></span>')

        return



    @_qc.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject')    
    def apply_hv_settings(self, module_key, channel_key):
        if not self.module.is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
        self.host_module.stop_reader_thread()
        while self.module.board_occupied:
            time.sleep(0.2)
        self.module.board_occupied = True
        
        ramp_speed_text = self.ramp_speed_field.text().strip()
        set_voltage_text = self.set_voltage_field.text().strip()
        min_trip_time_text = self.time_between_trips_field.text().strip()
        print("try")
        try:
            if ramp_speed_text:
                ramp_speed = abs(int(float(ramp_speed_text)))
            else:
                ramp_speed = int(float(self.ramp_speed_field.placeholderText()))
                
            if set_voltage_text:
                set_voltage = abs(int(float(set_voltage_text)))
            else:
                set_voltage = int(float(self.set_voltage_field.placeholderText()))
                
            if min_trip_time_text:
                set_min_trip_time = abs(float(min_trip_time_text))
            else:
                set_min_trip_time = float(self.time_between_trips_field.placeholderText())

        except (ValueError, TypeError):
            self.err_msg_set_hv_values = _qw.QMessageBox.warning(self, "Values",
            "Invalid input for the Board parameters!")
            self.module.board_occupied = False
       	    self.host_module.start_reader_thread()
            return False

        if self.channel.write_ramp_speed(ramp_speed):
            self.err_msg_set_hv_values_speed = _qw.QMessageBox.warning(self, "Set Ramp speed", 
            "Invalid response from HV Channel for set Ramp speed. Check values!")
            self.module.board_occupied = False            
            self.host_module.start_reader_thread()
            return False
        if channel.write_set_voltage(set_voltage):
            self.err_msg_set_hv_values_voltage = _qw.QMessageBox.warning(self, "Set Voltage",
                           	"Invalid response from HV Channel for set Voltage. Check values!")
            self.module.board_occupied = False
            self.host_module.start_reader_thread()
            return False
        self.channel.min_time_trips = set_min_trip_time
        self.ramp_speed_field.setText("")
        self.set_voltage_field.setText("")
        self.time_between_trips_field.setText("")
        # This is neccessary to delete the current saved value and make the change clear
        self.channel.set_voltage = float('nan')
        self.channel.ramp_speed = float('nan')
        self.ramp_speed_field.setPlaceholderText("")
        self.set_voltage_field.setPlaceholderText("")
        self.time_between_trips_field.setPlaceholderText("")  

        self.module.board_occupied = False         
        self.host_module.start_reader_thread()
        return True        
        


class nhr_channel_tab(gen_channel_tab):

    def __init__(self, host_widget, this_channel):
        super().__init__(host_widget, this_channel)
        
    def _init_channel_tab(self):
        super()._init_channel_tab()
        # Push button to change board polarity
        self.change_pol_button = _qw.QPushButton("toggle")
        self.change_pol_button.setToolTip("Toggle the polarity of the channel. (Only possible if HV is off, and output is close to zero volt)")
        self.change_pol_button.setFixedWidth(70)
        self.change_pol_button.setEnabled(False)               
        self.change_pol_button.setStyleSheet("QPushButton {background-color: #9addf5;}")
        self.change_pol_button.clicked.connect(partial(self.change_channel_polarity))
        
        #### Push Buttons to apply settings and turn on HV
        self.apply_button = _qw.QPushButton("set")
        self.apply_button.setToolTip("Write Set voltage and Ramp speed to the board. Refresh dT setting.\n(If High-Voltage is on, the board will directly start to ramp!)")
        self.apply_button.setFixedWidth(70)
        #TODO
        #self.apply_button.clicked.connect(partial(self.apply_hv_settings, mod_key, channel_key)) 
        # connect the return key to the apply action
        self.time_between_trips_field.returnPressed.connect(self.apply_button.click)
        self.set_voltage_field.returnPressed.connect(self.apply_button.click)
        self.ramp_speed_field.returnPressed.connect(self.apply_button.click)                
        
        self.on_off_button = _qw.QPushButton("on/off")
        self.on_off_button.setToolTip("Turn High-Voltage On and Off \n(using the currently set values)")
        self.on_off_button.setFixedWidth(70)
        self.on_off_button.setStyleSheet("QPushButton {background-color: red;}")
        #TODO
        #self.start_button.clicked.connect(partial(self.start_hv_change, mod_key, channel_key))    
        
        self.grid.addWidget(self.change_pol_button, 1, 6, 2, 1, _qc.Qt.AlignHCenter)        
        self.grid.addWidget(self.apply_button, 9, 4, _qc.Qt.AlignHCenter)
        self.grid.addWidget(self.on_off_button, 9, 5, _qc.Qt.AlignHCenter)
        
        
    def update_channel_section(self):
        super().update_channel_section()
        
        # Enable/disable the change polarity button if Voltage is applied
        if self.host_module.is_connected:
            if (self.channel.hv_switch_off and abs(self.channel.voltage) <= 0.002 * self.voltage_limit):
                self.change_pol_button.setEnabled(True)
            else:
                self.change_pol_button.setEnabled(False)
        else:
            self.change_pol_button.setEnabled(False)


    def change_channel_polarity(self):
        if not self.module.is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
        self.host_module.stop_reader_thread()
        while self.module.board_occupied:
            time.sleep(0.2)
        self.module.board_occupied = True
        
        ramp_speed_text = self.ramp_speed_field.text().strip()
        set_voltage_text = self.set_voltage_field.text().strip()
        min_trip_time_text = self.time_between_trips_field.text().strip()
        print("Swapping polarity")
        if not self.channel.switch_polarity():
            self.err_msg_set_hv_values_speed = _qw.QMessageBox.warning(self, "Switch polarity", 
            "Invalid response from HV Channel for Polarity switch. Check values!")
            self.module.board_occupied = False            
            self.host_module.start_reader_thread()

        self.module.board_occupied = False         
        self.host_module.start_reader_thread()        
        

            

        
    '''        
        
    def update_channel_section(self, mod_key, channel_key):



        # check for trips, and auto-reramp
        if not _np.isnan(this_channel.voltage):
            if self.all_channels_trip_detect_box[mod_key][channel_key].checkState():
                if (abs(this_channel.voltage) < this_channel.trip_voltage):
                    if not this_channel.trip_detected:
                        # channel is probably tripped
                        this_channel.trip_detected = True        
                        this_channel.trip_time_stamps.append(time.time())
                        if len(this_channel.trip_time_stamps) < 2:
                            dt_last_trip = this_channel.min_time_trips*60
                        else:
                            dt_last_trip = time.time() - this_channel.trip_time_stamps[-2]    
                        if dt_last_trip < this_channel.min_time_trips*60:
                            # This was a frequent trip
                            self.send_mail(mod_key, channel_key, "frequent")   
                            this_channel.auto_reramp_mode = "freq_trip"
                        else:
                            # This was a single trip
                            self.send_mail(mod_key, channel_key, "single")
                            if not this_channel.manual_control:
                                if self.all_channels_auto_reramp_box[mod_key][channel_key].checkState():
                                    if not (_np.isnan(self.channels[mod_key][channel_key].set_voltage) or _np.isnan(self.channels[mod_key][channel_key].ramp_speed)):
                                        if self.interlock_value:
                                            self.start_hv_change(mod_key, channel_key, True)
                                            #self.stop_reader_thread(self.modules[mod_key])
                                            #self.channels[mod_key][channel_key].read_status()
                                            #answer = self.channels[mod_key][channel_key].start_voltage_change()
                                            #self.start_reader_thread(self.modules[mod_key])
                                        
                else:
                    this_channel.trip_detected = False
                    if self.all_channels_auto_reramp_box[mod_key][channel_key].checkState():
                        this_channel.auto_reramp_mode = "on"
                    else:
                        this_channel.auto_reramp_mode = "off"
                    if this_channel.manual_control:
                        this_channel.auto_reramp_mode = "no_dac"
          
        self.all_channels_time_between_trips_field[mod_key][channel_key].setPlaceholderText(str(this_channel.min_time_trips))        
        self.all_channels_set_voltage_field[mod_key][channel_key].setPlaceholderText(str(this_channel.set_voltage))
        self.all_channels_ramp_speed_field[mod_key][channel_key].setPlaceholderText(str(this_channel.ramp_speed))
        
        return
            
        


    @_qc.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')      
    def change_channel_hv_field(self, module_key, channel_key, set_voltage, ramp_speed):
        
        channel = self.channels[module_key][channel_key]
        if not self.modules[module_key].is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
        self.stop_reader_thread(self.modules[module_key])
        while self.modules[module_key].board_occupied:
            time.sleep(0.2)
        self.modules[module_key].board_occupied = True
        
        print("try")
        try:
            ramp_speed_int = abs(int(float(ramp_speed)))
            set_voltage_int = abs(int(float(set_voltage)))

        except (ValueError, TypeError):
            self.err_msg_set_hv_values = _qw.QMessageBox.warning(self, "Values",
            "Invalid input for the Board parameters!")
            self.modules[module_key].board_occupied = False
       	    self.start_reader_thread(self.modules[module_key])
            return False

        if channel.write_ramp_speed(ramp_speed_int):
            self.err_msg_set_hv_values_speed = _qw.QMessageBox.warning(self, "Set Ramp speed", 
            "Invalid response from HV Channel for set Ramp speed. Check values!")
            self.modules[module_key].board_occupied = False            
            self.start_reader_thread(self.modules[module_key])
            return False
        if channel.write_set_voltage(set_voltage_int):
            self.err_msg_set_hv_values_voltage = _qw.QMessageBox.warning(self, "Set Voltage",
                           	"Invalid response from HV Channel for set Voltage. Check values!")
            self.modules[module_key].board_occupied = False
            self.start_reader_thread(self.modules[module_key])
            return False

        self.all_channels_ramp_speed_field[module_key][channel_key].setText("")
        self.all_channels_set_voltage_field[module_key][channel_key].setText("")
        self.all_channels_time_between_trips_field[module_key][channel_key].setText("")
        # This is neccessary to delete the current saved value and make the change clear
        channel.set_voltage = float('nan')
        channel.ramp_speed = float('nan')
        self.all_channels_ramp_speed_field[module_key][channel_key].setPlaceholderText("")
        self.all_channels_set_voltage_field[module_key][channel_key].setPlaceholderText("")
        self.all_channels_time_between_trips_field[module_key][channel_key].setPlaceholderText("")  

        self.modules[module_key].board_occupied = False         
        self.start_reader_thread(self.modules[module_key])
        return True        



        
    @_qc.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')        
    def start_hv_change(self, module_key, channel_key, auto=False):
        if not self.modules[module_key].is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
            
        if _np.isnan(self.channels[module_key][channel_key].set_voltage) or _np.isnan(self.channels[module_key][channel_key].ramp_speed):
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Channel", 
                "Channel shows invalid value!")        
            return False
        if not (self.locker.lock_state and self.interlock_value):
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Interlock", 
                "Interlock is/was triggered! Abort Voltage change!")        
            return False

        confirmation = auto
        if not auto:
            answer = _qw.QMessageBox.question(self, "Are you sure?", 
            "You are about to ramp channel: "+self.channels[module_key][channel_key].name+
            "\nSet Voltage: "+str(self.channels[module_key][channel_key].set_voltage)+
            "\nRamp Speed: "+str(self.channels[module_key][channel_key].ramp_speed)+
            "\nPlease Confirm!", _qw.QMessageBox.Yes, _qw.QMessageBox.No)
            confirmation = (answer == _qw.QMessageBox.Yes)
        self.stop_reader_thread(self.modules[module_key])
        while self.modules[module_key].board_occupied:
            time.sleep(0.2)        
        self.modules[module_key].board_occupied = True
        
        if confirmation:
            self.channels[module_key][channel_key].read_status()        
            answer = self.channels[module_key][channel_key].start_voltage_change()
            if not ("H2L" in answer or "L2H" in answer or "ON" in answer):
                self.err_msg_voltage_change = _qw.QMessageBox.warning(self, "Voltage Change",
               	"Invalid response from HV Channel. Check values!")
       	        self.modules[module_key].board_occupied = False
               	self.start_reader_thread(self.modules[module_key])
               	return False
            else:
                if not auto:
                    self.err_msg_voltage_change_good = _qw.QMessageBox.information(self, "Voltage Change",
                    "Voltage is changing!")
       	        self.modules[module_key].board_occupied = False
                self.start_reader_thread(self.modules[module_key])
                return True
        else:
            self.err_msg_voltage_change_abort = _qw.QMessageBox.warning(self, "Voltage Change",
               	"Operation aborted!")
            self.modules[module_key].board_occupied = False
            self.start_reader_thread(self.modules[module_key])
            return False
            
    '''            
            
            

