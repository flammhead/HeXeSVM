"""Contains the HeXeSVM User interface"""

import sys
import logging as _lg
import sqlalchemy as _sql
import numpy as _np
from datetime import datetime as _dt
import time
from collections import OrderedDict
from PyQt5 import QtCore as _qc
from PyQt5 import QtGui as _qg
from PyQt5 import QtWidgets as _qw
from PyQt5 import QtSvg as _qs
from functools import partial

from hexesvm import iSeg_tools as _iseg
from hexesvm.sql_io_writer import SqlWriter as _sql_writer
from hexesvm.interlock import Interlock as _interlock
from hexesvm import threads as _thr 
from hexesvm import mail as _mail



# create module logger
_gui_log = _lg.getLogger("hexesvm.gui")
_gui_log.setLevel(_lg.DEBUG)
_lg.debug("Loading hexesvm.gui")


class MainWindow(_qw.QMainWindow):

    log = _lg.getLogger("hexesvm.gui.MainWindow")

    def __init__(self):

        super().__init__()
        MainWindow.log.debug("Created MainWindow")
        # create the iSeg modules
        self._initialize_hv_modules()
        # create email notifier 
        self.email_sender = _mail.MailNotifier()
        # create interlocker
        self.locker = _interlock()
        self.interlock_value = True
        # create database flag
        self.db_connection = False
        self.db_connection_write = False
        self.output_buffer_file = open("tempdata_log.dat", 'a')

        timer = _qc.QTimer(self)
        timer.timeout.connect(self.updateUI)
        timer.start(1000)

        self.startUI()
        self.updateUI()
                
    def startUI(self):
		
        self._init_geom()
        self._init_menu()
        self._init_status_bar()
        self._init_subwindows()
        
                
        
    def updateUI(self):

        self.update_status_bar()
        self.update_overview()
        self.update_module_tabs()
        

    def _initialize_hv_modules(self):		

        self.modules = OrderedDict(
        {"PMT module": _iseg.hv_module("pmt module", "COM7"),
        "Anode module": _iseg.hv_module("anode module", "COM17"),
        "Drift module": _iseg.hv_module("drift module", "COM18")})		        
                
        self.channel_order_dict = ((("PMT module", "Top PMT"), ("Anode module", "Anode"), 
                          ("Drift module", "Gate"), ("Drift module", "Cathode"),
                          ("PMT module", "Bottom PMT")))
                          
        self.channels = OrderedDict(
        {"PMT module": {"Top PMT": self.modules["PMT module"].add_channel(1, "top pmt"),
                        "Bottom PMT": self.modules["PMT module"].add_channel(2, "bottom pmt")},
         "Anode module": {"Anode": self.modules["Anode module"].add_channel(2, "anode")},
         "Drift module": {"Gate": self.modules["Drift module"].add_channel(2, "gate"),
                          "Cathode": self.modules["Drift module"].add_channel(1, "cathode")}})

        
    def kill_all_hv(self):
        MainWindow.log.debug("Called KILL ALL HV method!")
        response = []
        message = "High Voltage KILL was triggered and performed!\nModule responses:"        
        # Tell the threads of all modules to terminate
        for key in self.modules.keys():
            if not self.modules[key].is_connected:
                continue
            self.modules[key].stop_running_thread()      

        for pair in self.channel_order_dict:
            self.all_channels_auto_reramp_box[pair[0]][pair[1]].setCheckState(False)
            self.all_channels_auto_reramp_box[pair[0]][pair[1]].setEnabled(False)

        for key in self.modules.keys():
            if not self.modules[key].is_connected:
                continue
            while self.modules[key].board_occupied:
                MainWindow.log.debug("Waiting for thread "+key+" to stop"+str(self.modules[key].stop_thread))
                time.sleep(0.2)
            MainWindow.log.debug("thread "+key+" stopped")                
            response_mod = self.modules[key].kill_hv()
            response.append((key, response_mod))
            message+="\n"+key+"\t"+str(response_mod)
        # restart the reader threads
        for key in self.modules.keys():
            if not self.modules[key].is_connected:
                continue        
            self.start_reader_thread(self.modules[key])               
        
        self.hv_kill_msg = _qw.QMessageBox.warning(self, "HV Kill", message)
        MainWindow.log.debug(response)
        
    def update_interlock(self):
        # if too slow, the interlocker must be outsourced to an own thread?
        response = self.locker.check_interlock()
        if not response and self.locker.is_running:
            if self.interlock_value:
                self.kill_all_hv()
                self.locker.lock_state = False
                self.interlock_value = False

    def _init_geom(self):
        """Initializes the main window's geometry"""
        MainWindow.log.debug("Called MainWindow._init_geom")
        # set basic attributes
        self.setAttribute(_qc.Qt.WA_DeleteOnClose)
        self.setWindowTitle("HeXeSVM (pre-alpha)")
        self.resize(640, 480)

        # center window
        win_geom = self.frameGeometry()
        desk_center = _qw.QDesktopWidget().availableGeometry().center()
        win_geom.moveCenter(desk_center)
        self.move(win_geom.topLeft())


    def _init_menu(self):
        """Initializes the menu"""
        # define file menu and entries

        MainWindow.log.debug("Called MainWindow._init_menu")
        self.file_menu = _qw.QMenu("&File", self)
        self.file_menu.addAction("&Quit", self.file_quit,
		                 _qc.Qt.CTRL + _qc.Qt.Key_Q)


        self.menuBar().addMenu(self.file_menu)


    def _init_status_bar(self):
        """Initializes the status bar"""
        MainWindow.log.debug("Called MainWindow._init_status_bar")

        self.statusBar().showMessage('Program started')
        sep_middle = _qw.QLabel("")
        sep_middle.setFrameStyle(_qw.QFrame.VLine)

        self.interlock_widget = _qw.QLabel("Interlock: ")
        self.statusBar().addPermanentWidget(self.interlock_widget)
        self.statusBar().addPermanentWidget(sep_middle)
        self.database_widget = _qw.QLabel("Database: ")
        self.statusBar().addPermanentWidget(self.database_widget)
        self.update_status_bar()

    def update_status_bar(self):
        self.update_interlock()
        if self.locker.lock_state:
            new_palette = self.interlock_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(0,204,0))
            self.interlock_widget.setPalette(new_palette)
            self.interlock_widget.setText("Interlock: OK ("
                                            +str(self.locker.parameter_value)+" bar)")
        else:
            new_palette = self.interlock_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(255,0,0))
            self.interlock_widget.setPalette(new_palette)
            self.interlock_widget.setText("Interlock: ERROR ("
                                        +str(self.locker.parameter_value)+")")

        if self.db_connection_write:
            new_palette = self.database_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(0,204,0))
            self.database_widget.setPalette(new_palette)
            self.database_widget.setText("Database: OK")
        else:
            new_palette = self.database_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(255,0,0))
            self.database_widget.setPalette(new_palette)
            self.database_widget.setText("Database: ERROR")
        return


    def _init_subwindows(self):
        """Create the tabs"""
        MainWindow.log.debug("Called MainWindow._init_subwindows")
        self.main_widget = _qw.QTabWidget(self)
        self.setCentralWidget(self.main_widget)
        self.overviewTab = _qw.QWidget(self.main_widget)
        self.settingsTab = _qw.QWidget(self.main_widget)
        self.main_widget.addTab(self.overviewTab, "Overview")
        # create tabs for the HV modules here
        self.mod_tabs = {}
        for key, mod in self.modules.items():
            this_tab = _qw.QWidget(self.main_widget)
            self.mod_tabs.update({key: this_tab})
            self.main_widget.addTab(this_tab, key)

        self.main_widget.addTab(self.settingsTab, "Settings")
		
        self._init_settings()
        self._init_module_tabs()
        self._init_overview()

    def _init_module_tabs(self):
    
        self.module_com_labels = []
        self.module_com_line_edits = []
        self.module_is_high_precission_labels = []        
        self.module_is_high_precission_boxes = []
        self.module_connect_buttons = []
        self.module_disconnect_buttons = []           
        self.module_umax_labels = []
        self.module_umax_fields = []        
        self.module_imax_labels = []
        self.module_imax_fields = []
        self.module_serial_labels = []
        self.module_serial_fields = []        
        self.module_firmware_labels = []
        self.module_firmware_fields = []
        self.module_hsep = []              
        self.module_vsep = []                            
        self.module_grid_layouts = []

        # create these as nested dictionaries
        self.all_channels_error_sign = {}
        self.all_channels_trip_sign = {}
        self.all_channels_inhibit_sign = {}
        self.all_channels_kill_sign = {}
        self.all_channels_hv_on_sign = {}
        self.all_channels_dac_on_sign = {}
        self.all_channels_hv_ramp_sign = {}
        self.all_channels_trip_rate_field = {}
        self.all_channels_single_button_group = {}
        self.all_channels_single_none_button = {}
        self.all_channels_single_info_button = {}
        self.all_channels_single_alarm_button = {}
        self.all_channels_frequent_button_group = {}
        self.all_channels_frequent_info_button = {}
        self.all_channels_frequent_alarm_button = {}
        self.all_channels_number_label = {}
        self.all_channels_polarity_label = {}
        self.all_channels_trip_detect_box = {}
        self.all_channels_auto_reramp_box = {}
        self.all_channels_time_between_trips_field = {}
        self.all_channels_set_voltage_field = {}
        self.all_channels_ramp_speed_field = {}
        self.all_channels_apply_button = {}
        self.all_channels_start_button = {}
        
        MainWindow.log.debug("Called MainWindow._init_module_tabs")
        for i, key in zip(range(len(self.modules)), self.modules.keys()):

            self.all_channels_error_sign.update({key: {}})
            self.all_channels_trip_sign.update({key: {}})
            self.all_channels_inhibit_sign.update({key: {}})
            self.all_channels_kill_sign.update({key: {}})
            self.all_channels_hv_on_sign.update({key: {}})
            self.all_channels_dac_on_sign.update({key: {}})
            self.all_channels_hv_ramp_sign.update({key: {}})
            self.all_channels_trip_rate_field.update({key: {}})
            self.all_channels_single_button_group.update({key: {}})
            self.all_channels_single_none_button.update({key: {}})
            self.all_channels_single_info_button.update({key: {}})
            self.all_channels_single_alarm_button.update({key: {}})
            self.all_channels_frequent_button_group.update({key: {}})
            self.all_channels_frequent_info_button.update({key: {}})
            self.all_channels_frequent_alarm_button.update({key: {}})
            self.all_channels_number_label.update({key: {}})
            self.all_channels_polarity_label.update({key: {}})
            self.all_channels_trip_detect_box.update({key: {}})
            self.all_channels_auto_reramp_box.update({key: {}})
            self.all_channels_time_between_trips_field.update({key: {}})
            self.all_channels_set_voltage_field.update({key: {}})
            self.all_channels_ramp_speed_field.update({key: {}})
            self.all_channels_apply_button.update({key: {}})
            self.all_channels_start_button.update({key: {}})

            this_tab = self.mod_tabs[key]
            this_module = self.modules[key]
    
            this_com_port_label = _qw.QLabel("Port:")
            self.module_com_labels.append(this_com_port_label)
            this_com_port = _qw.QLineEdit(this_tab)
            this_com_port.setText(this_module.port)
            self.module_com_line_edits.append(this_com_port)
            #this_com_port.returnPressed.connect(this_connect_button.click)
            
            this_high_precision_label = _qw.QLabel("High precision:")
            self.module_is_high_precission_labels.append(this_high_precision_label)
            this_high_precision_box = _qw.QCheckBox(this_tab)
            self.module_is_high_precission_boxes.append(this_high_precision_box)
            
            this_connect_button = _qw.QPushButton("connect")
            self.module_connect_buttons.append(this_connect_button)
            this_connect_button.clicked.connect(partial(self.connect_hv_module, key, i))
            
            this_disconnect_button = _qw.QPushButton("disconnect")
            this_disconnect_button.setEnabled(False)               
            self.module_disconnect_buttons.append(this_disconnect_button)
            this_disconnect_button.clicked.connect(partial(self.disconnect_hv_module, key, i))      
            
            this_u_max_label = _qw.QLabel("U(V):")
            self.module_umax_labels.append(this_u_max_label)
            this_u_max_field = _qw.QLineEdit(this_tab)
            this_u_max_field.setDisabled(True)
            self.module_umax_fields.append(this_u_max_field)
            
            this_i_max_label = _qw.QLabel("I(mA):")
            self.module_imax_labels.append(this_i_max_label)
            this_i_max_field = _qw.QLineEdit(this_tab)
            this_i_max_field.setDisabled(True)
            self.module_imax_fields.append(this_i_max_field)            

            this_serial_number_label = _qw.QLabel("Serial:")
            self.module_serial_labels.append(this_serial_number_label)
            this_serial_number_field = _qw.QLineEdit(this_tab)
            this_serial_number_field.setDisabled(True)
            self.module_serial_fields.append(this_serial_number_field)  
            
            this_firmware_label = _qw.QLabel("Firmware:")
            self.module_firmware_labels.append(this_firmware_label)
            this_firmware_field = _qw.QLineEdit(this_tab)
            this_firmware_field.setDisabled(True)
            self.module_firmware_fields.append(this_firmware_field)    
            
            horizontal_separator = _qw.QLabel("")
            self.module_hsep.append(horizontal_separator)
            horizontal_separator.setFrameStyle(_qw.QFrame.HLine)
            horizontal_separator.setLineWidth(2)
            vertical_separator = _qw.QLabel("")
            vertical_separator.setFrameStyle(_qw.QFrame.VLine)
            vertical_separator.setLineWidth(2)
        
            grid = _qw.QGridLayout()
            grid.setSpacing(10)
            # Row 1 widgetd
            grid.addWidget(this_com_port_label, 1,2)
            grid.addWidget(this_com_port, 1,3,1,2)
            grid.addWidget(this_high_precision_label, 1, 7)
            grid.addWidget(this_high_precision_box, 1,8)
            # Row 2 widgets
            grid.addWidget(this_connect_button, 2,2, 1,4, _qc.Qt.AlignHCenter)
            grid.addWidget(this_disconnect_button, 2,7, 1,4, _qc.Qt.AlignHCenter)            
            # Row 3 widgets
            grid.addWidget(this_u_max_label, 3,1)
            grid.addWidget(this_u_max_field, 3,2)
            grid.addWidget(this_i_max_label, 3,3)
            grid.addWidget(this_i_max_field, 3,4)
            grid.addWidget(this_serial_number_label, 3,6)
            grid.addWidget(this_serial_number_field, 3,7)  
            grid.addWidget(this_firmware_label, 3,8)
            grid.addWidget(this_firmware_field, 3,9)
            # Row 4 widget (horizontal separator)
            grid.addWidget(horizontal_separator, 4,1,1,9)
            
            if len(self.channels[key].keys()) > 0:
                channel_grid_1 = self._init_channel_section(key, list(self.channels[key].keys())[0])
                grid.addLayout(channel_grid_1, 5,1, 8,4)
            if len(self.channels[key].keys()) > 1:
                channel_grid_2 = self._init_channel_section(key, list(self.channels[key].keys())[1])
                grid.addLayout(channel_grid_2, 5,6, 8,4)            
            
            grid.addWidget(vertical_separator, 5, 5, 8, 1)
            this_tab.setLayout(grid)
            
            self.module_grid_layouts.append(grid)
            
        self.update_module_tabs()   

        return

    def _init_channel_section(self, mod_key, channel_key):
        this_tab = self.mod_tabs[mod_key]
        this_channel = self.channels[mod_key][channel_key]
        
        # Toggle indicator lights (left)
        this_channel_name_label = _qw.QLabel('<span style="font-size:large"><b>'+channel_key+"</b></span>")
        this_channel_error_label = _qw.QLabel("Error")
        this_channel_error_sign = _qw.QLabel()
        this_channel_error_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.all_channels_error_sign[mod_key].update({channel_key: this_channel_error_sign})
        this_channel_trip_label = _qw.QLabel("Trip")
        this_channel_trip_sign = _qw.QLabel()
        this_channel_trip_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.all_channels_trip_sign[mod_key].update({channel_key: this_channel_trip_sign})
        this_channel_inhibit_label = _qw.QLabel("Inhibit")
        this_channel_inhibit_sign = _qw.QLabel()
        this_channel_inhibit_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.all_channels_inhibit_sign[mod_key].update({channel_key: this_channel_inhibit_sign})
        this_channel_kill_label = _qw.QLabel("Kill")
        this_channel_kill_sign = _qw.QLabel()
        this_channel_kill_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.all_channels_kill_sign[mod_key].update({channel_key: this_channel_kill_sign})
        this_channel_hv_on_label = _qw.QLabel("HV on")
        this_channel_hv_on_sign = _qw.QLabel()
        this_channel_hv_on_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.all_channels_hv_on_sign[mod_key].update({channel_key: this_channel_hv_on_sign})
        this_channel_dac_on_label = _qw.QLabel("DAC on")
        this_channel_dac_on_sign = _qw.QLabel()
        this_channel_dac_on_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg'))
        self.all_channels_dac_on_sign[mod_key].update({channel_key: this_channel_dac_on_sign})
        this_channel_hv_ramp_label = _qw.QLabel("HV ramp")
        this_channel_hv_ramp_sign = _qw.QLabel()
        this_channel_hv_ramp_sign.setPixmap(_qg.QPixmap('hexesvm/icons/hexe_bar.svg'))
        self.all_channels_hv_ramp_sign[mod_key].update({channel_key: this_channel_hv_ramp_sign})
        this_channel_trip_rate_label = _qw.QLabel("Trips (24hrs)")
        this_channel_trip_rate_field = _qw.QLineEdit(this_tab)
        this_channel_trip_rate_field.setDisabled(True)
        self.all_channels_trip_rate_field[mod_key].update({channel_key: this_channel_trip_rate_field})
        # email alarm settings (bottom)
        this_channel_email_settings_label = _qw.QLabel("<b>Alarm settings:</b>")
        this_channel_single_trip_settings_label = _qw.QLabel("Single trip")
        this_channel_frequent_trip_label = _qw.QLabel("Frequent trip")
        this_channel_none_settings_label = _qw.QLabel("none")
        this_channel_info_settings_label = _qw.QLabel("info")
        this_channel_alarm_settings_label = _qw.QLabel("alarm")
        this_channel_single_button_group = _qw.QButtonGroup(this_tab)
        this_channel_single_none_button = _qw.QRadioButton()
        this_channel_single_button_group.addButton(this_channel_single_none_button, 0)                        
        this_channel_single_info_button = _qw.QRadioButton()
        this_channel_single_info_button.setChecked(True)
        this_channel_single_button_group.addButton(this_channel_single_info_button, 1)
        this_channel_single_alarm_button = _qw.QRadioButton()        
        this_channel_single_button_group.addButton(this_channel_single_alarm_button, 2)
        self.all_channels_single_button_group[mod_key].update({channel_key: this_channel_single_button_group})
        this_channel_frequent_button_group = _qw.QButtonGroup(this_tab)               
        this_channel_frequent_none_button = _qw.QRadioButton()
        this_channel_frequent_button_group.addButton(this_channel_frequent_none_button, 0)                
        this_channel_frequent_info_button = _qw.QRadioButton()
        this_channel_frequent_button_group.addButton(this_channel_frequent_info_button, 1)        
        this_channel_frequent_alarm_button = _qw.QRadioButton()
        this_channel_frequent_alarm_button.setChecked(True)        
        this_channel_frequent_button_group.addButton(this_channel_frequent_alarm_button, 2) 
        self.all_channels_frequent_button_group[mod_key].update({channel_key: this_channel_frequent_button_group})
        this_channel_single_test_button = _qw.QPushButton("test")
        this_channel_frequent_test_button = _qw.QPushButton("test")
        this_channel_single_test_button.clicked.connect(partial(self.send_mail, this_channel, this_channel_single_button_group.checkedId()))
        this_channel_frequent_test_button.clicked.connect(partial(self.send_mail, this_channel, this_channel_frequent_button_group.checkedId()))

        # separator for controls
        this_channel_vertical_separator = _qw.QLabel("")
        this_channel_vertical_separator.setFrameStyle(_qw.QFrame.VLine)
              
        # controls of the channel (right)
        if this_channel.channel == 1:
            this_channel_number_label = _qw.QLabel('<span style="font-size:xx-large"><b>A</b></span>')
        elif this_channel.channel == 2:
            this_channel_number_label = _qw.QLabel('<span style="font-size:xx-large"><b>B</b></span>')
        else:
            this_channel_number_label = _qw.QLabel('<span style="font-size:xx-large"><b>?</b></span>')
        self.all_channels_number_label[mod_key].update({channel_key: this_channel_number_label})
        
        if this_channel.polarity_positive == True:
            this_channel_polarity_label = _qw.QLabel('<span style="font-size:xx-large"><b><font color="red">+</font></b></span>')
        elif this_channel.polarity_positive == False:
            this_channel_polarity_label = _qw.QLabel('<span style="font-size:xx-large"><b><font color="#00ff00">-</font></b></span>')
        else:
            this_channel_polarity_label = _qw.QLabel('<span style="font-size:xx-large"><b>+/-</b></span>')
        self.all_channels_polarity_label[mod_key].update({channel_key: this_channel_polarity_label})
        this_channel_control_label = _qw.QLabel("<b>Control</b>")
        
        this_channel_trip_detect_box = _qw.QCheckBox("detect trips", this_tab)
        self.all_channels_trip_detect_box[mod_key].update({channel_key: this_channel_trip_detect_box})
        this_channel_auto_reramp_box = _qw.QCheckBox("auto re-ramp", this_tab)
        self.all_channels_auto_reramp_box[mod_key].update({channel_key: this_channel_auto_reramp_box})
        
        # this ensures, that trip detect is active when auto reramp is on (sorry for sausage code.
        self.all_channels_trip_detect_box[mod_key][channel_key].toggled.connect(lambda a: self.all_channels_auto_reramp_box[mod_key][channel_key].setChecked(a and self.all_channels_auto_reramp_box[mod_key][channel_key].checkState()))        
        self.all_channels_auto_reramp_box[mod_key][channel_key].toggled.connect(lambda a: self.all_channels_trip_detect_box[mod_key][channel_key].setChecked(a or self.all_channels_trip_detect_box[mod_key][channel_key].checkState()))
        
        this_channel_time_between_trips_label = _qw.QLabel("dT(frequent) (min)")
        this_channel_time_between_trips_field = _qw.QLineEdit(this_tab)
        self.all_channels_time_between_trips_field[mod_key].update({channel_key: this_channel_time_between_trips_field})
        this_channel_set_voltage_label = _qw.QLabel("Set voltage (V)")
        this_channel_set_voltage_field = _qw.QLineEdit(this_tab)
        self.all_channels_set_voltage_field[mod_key].update({channel_key: this_channel_set_voltage_field})
        this_channel_ramp_speed_label = _qw.QLabel("Ramp speed (V/s)")
        this_channel_ramp_speed_field = _qw.QLineEdit(this_tab)        
        self.all_channels_ramp_speed_field[mod_key].update({channel_key: this_channel_ramp_speed_field})
        this_channel_apply_button = _qw.QPushButton("apply")
        this_channel_apply_button.setFixedWidth(70)
        this_channel_apply_button.clicked.connect(partial(self.apply_hv_settings, mod_key, channel_key))
        self.all_channels_apply_button[mod_key].update({channel_key: this_channel_apply_button})
        this_channel_start_button = _qw.QPushButton("start")
        this_channel_start_button.setFixedWidth(70)
        this_channel_start_button.setStyleSheet("QPushButton {background-color: red;}");        
        this_channel_start_button.clicked.connect(partial(self.start_hv_change, mod_key, channel_key))    
        self.all_channels_start_button[mod_key].update({channel_key: this_channel_start_button})                 
              
        grid = _qw.QGridLayout()
        grid.setSpacing(5)
        
        grid.addWidget(this_channel_name_label, 1,1)
        grid.addWidget(this_channel_error_label, 2,1)
        grid.addWidget(this_channel_error_sign, 2,2)
        grid.addWidget(this_channel_trip_label, 3,1)
        grid.addWidget(this_channel_trip_sign, 3,2)
        grid.addWidget(this_channel_inhibit_label, 4,1)
        grid.addWidget(this_channel_inhibit_sign, 4,2)
        grid.addWidget(this_channel_kill_label, 5,1)
        grid.addWidget(this_channel_kill_sign, 5,2)
        grid.addWidget(this_channel_hv_on_label, 6,1)
        grid.addWidget(this_channel_hv_on_sign, 6,2)
        grid.addWidget(this_channel_dac_on_label, 7,1)
        grid.addWidget(this_channel_dac_on_sign, 7,2)
        grid.addWidget(this_channel_hv_ramp_label, 8,1)
        grid.addWidget(this_channel_hv_ramp_sign, 8,2)
        grid.addWidget(this_channel_trip_rate_label, 9,1)
        grid.addWidget(this_channel_trip_rate_field, 9,2)

        grid.addWidget(this_channel_email_settings_label, 10, 1)
        grid.addWidget(this_channel_single_trip_settings_label, 11, 1)
        grid.addWidget(this_channel_frequent_trip_label, 12, 1)
        grid.addWidget(this_channel_none_settings_label, 10, 2, _qc.Qt.AlignHCenter)        
        grid.addWidget(this_channel_info_settings_label, 10, 3, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_alarm_settings_label, 10, 4, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_single_none_button, 11 , 2, _qc.Qt.AlignHCenter)      
        grid.addWidget(this_channel_single_info_button, 11, 3,_qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_single_alarm_button, 11, 4, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_frequent_none_button, 12, 2, _qc.Qt.AlignHCenter)        
        grid.addWidget(this_channel_frequent_info_button, 12, 3, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_frequent_alarm_button, 12, 4, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_single_test_button, 11, 5, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_frequent_test_button, 12, 5, _qc.Qt.AlignHCenter) 

        grid.addWidget(this_channel_vertical_separator, 1, 3, 9, 1)
        
        grid.addWidget(this_channel_number_label, 1, 4, 2,1,_qc.Qt.AlignLeft)
        grid.addWidget(this_channel_polarity_label, 1, 5,2,1, _qc.Qt.AlignRight)
        grid.addWidget(this_channel_control_label, 3, 4)
        grid.addWidget(this_channel_trip_detect_box, 4, 4, 1, 2)
        grid.addWidget(this_channel_auto_reramp_box, 5, 4, 1, 2)
        grid.addWidget(this_channel_time_between_trips_label, 6, 4)
        grid.addWidget(this_channel_time_between_trips_field, 6, 5)
        grid.addWidget(this_channel_set_voltage_label, 7, 4)
        grid.addWidget(this_channel_set_voltage_field, 7, 5)
        grid.addWidget(this_channel_ramp_speed_label, 8, 4)
        grid.addWidget(this_channel_ramp_speed_field, 8, 5)
        grid.addWidget(this_channel_apply_button, 9, 4, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_start_button, 9, 5, _qc.Qt.AlignHCenter)
        
        return grid
        
    def update_module_tabs(self):
        MainWindow.log.debug("Called MainWindow.update_module_tabs")
        for i, key in zip(range(len(self.modules)), self.modules.keys()):    
            this_tab = self.mod_tabs[key]
            this_module = self.modules[key]
            
            self.module_umax_fields[i].setText(this_module.u_max)
            self.module_imax_fields[i].setText(this_module.i_max)
            self.module_serial_fields[i].setText(this_module.model_no)
            self.module_firmware_fields[i].setText(this_module.firmware_vers)
            
            if len(self.channels[key].keys()) > 0:
                self.update_channel_section(key, list(self.channels[key].keys())[0])
            if len(self.channels[key].keys()) > 1:
                self.update_channel_section(key, list(self.channels[key].keys())[1])
                
        return
        
    def update_channel_section(self, mod_key, channel_key):
        this_tab = self.mod_tabs[mod_key]
        this_channel = self.channels[mod_key][channel_key]
        
        none_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg')
        ok_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_green_small.svg')
        err_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_red_small.svg')
        
        if this_channel.channel_in_error is None:
            self.all_channels_error_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.channel_in_error is True:
            self.all_channels_error_sign[mod_key][channel_key].setPixmap(err_pix)        
        elif this_channel.channel_in_error is False:
            self.all_channels_error_sign[mod_key][channel_key].setPixmap(ok_pix)
            
        if this_channel.channel_is_tripped is None:
            self.all_channels_trip_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.channel_is_tripped is True:
            self.all_channels_trip_sign[mod_key][channel_key].setPixmap(err_pix)        
        elif this_channel.channel_is_tripped is False:
            self.all_channels_trip_sign[mod_key][channel_key].setPixmap(ok_pix)      
            
        if this_channel.hardware_inhibit is None:
            self.all_channels_inhibit_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.hardware_inhibit is True:
            self.all_channels_inhibit_sign[mod_key][channel_key].setPixmap(err_pix)        
        elif this_channel.hardware_inhibit is False:
            self.all_channels_inhibit_sign[mod_key][channel_key].setPixmap(ok_pix)          
            
        if this_channel.kill_enable_switch is None:
            self.all_channels_kill_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.kill_enable_switch is True:
            self.all_channels_kill_sign[mod_key][channel_key].setPixmap(err_pix)     
        elif this_channel.kill_enable_switch is False:
            self.all_channels_kill_sign[mod_key][channel_key].setPixmap(ok_pix)  
            
        if this_channel.hv_switch_off is None:
            self.all_channels_hv_on_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.hv_switch_off is True:
            self.all_channels_hv_on_sign[mod_key][channel_key].setPixmap(err_pix)        
        elif this_channel.hv_switch_off is False:
            self.all_channels_hv_on_sign[mod_key][channel_key].setPixmap(ok_pix)   
            
        if this_channel.manual_control is None:
            self.all_channels_dac_on_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.manual_control is True:
            self.all_channels_dac_on_sign[mod_key][channel_key].setPixmap(err_pix)
        elif this_channel.manual_control is False:
            self.all_channels_dac_on_sign[mod_key][channel_key].setPixmap(ok_pix)
        
        if this_channel.status == "":
            self.all_channels_hv_ramp_sign[mod_key][channel_key].setPixmap(none_pix)
        elif this_channel.status == "ON":
            self.all_channels_hv_ramp_sign[mod_key][channel_key].setPixmap(_qg.QPixmap('hexesvm/icons/hexe_bar.svg'))
        elif this_channel.status == "H2L":
            self.all_channels_hv_ramp_sign[mod_key][channel_key].setPixmap(_qg.QPixmap('hexesvm/icons/hexe_arrow_down.svg'))        
        elif this_channel.status == "L2H":                
            self.all_channels_hv_ramp_sign[mod_key][channel_key].setPixmap(_qg.QPixmap('hexesvm/icons/hexe_arrow_up.svg'))

        this_channel.trip_rate = 0
        now = time.time()
        for trip_time in this_channel.trip_time_stamps:
            if now - trip_time < 24*3600:
                this_channel.trip_rate += 1
        self.all_channels_trip_rate_field[mod_key][channel_key].setText(str(this_channel.trip_rate))
        
        this_channel_number_label = self.all_channels_number_label[mod_key][channel_key]
        if this_channel.channel == 1:
            this_channel_number_label = _qw.QLabel('<span style="font-size:xx-large"><b>A</b></span>')
        elif this_channel.channel == 2:
            this_channel_number_label = _qw.QLabel('<span style="font-size:xx-large"><b>B</b></span>')
        else:
            this_channel_number_label = _qw.QLabel('<span style="font-size:xx-large"><b>?</b></span>')
            
        this_channel_polarity_label = self.all_channels_polarity_label[mod_key][channel_key]
        if this_channel.polarity_positive is None:
            this_channel_polarity_label.setText('<span style="font-size:xx-large"><b>+/-</b></span>')
        elif this_channel.polarity_positive:
            this_channel_polarity_label.setText('<span style="font-size:xx-large"><b><font color="red">+</font></b></span>')
        else:
            this_channel_polarity_label.setText('<span style="font-size:xx-large"><b><font color="#00ff00">-</font></b></span>')

        # check for trips, and auto-reramp
        if not _np.isnan(this_channel.voltage):
            if self.all_channels_trip_detect_box[mod_key][channel_key].checkState():
                if (abs(this_channel.voltage) < this_channel.trip_voltage):
                    if not this_channel.trip_detected:
                        # channel is probably tripped
                        this_channel.trip_detected = True
                        single_priority = self.all_channels_single_button_group[mod_key][channel_key].checkedId()
                        self.send_mail(this_channel, single_priority, 1)            
                        this_channel.trip_time_stamps.append(time.time())
                        if len(this_channel.trip_time_stamps) < 2:
                            dt_last_trip = this_channel.min_time_trips*60
                        else:
                            dt_last_trip = time.time() - this_channel.trip_time_stamps[-2]    
                        if dt_last_trip < this_channel.min_time_trips*60:
                            freq_priority = self.all_channels_frequent_button_group[mod_key][channel_key].checkedId()
                            self.send_mail(this_channel, freq_priority, 2)         
                            this_channel.auto_reramp_mode = "freq_trip"
                        else:
                            if not this_channel.manual_control:
                                if self.all_channels_auto_reramp_box[mod_key][channel_key].checkState():
                                    if not (_np.isnan(self.channels[mod_key][channel_key].set_voltage) or _np.isnan(self.channels[mod_key][channel_key].ramp_speed)):
                                        if self.interlock_value:
                                            self.stop_reader_thread(self.modules[mod_key])
                                            self.channels[mod_key][channel_key].read_status()
                                            answer = self.channels[mod_key][channel_key].start_voltage_change()
                                            self.start_reader_thread(self.modules[mod_key])
                                        
                else:
                    this_channel.trip_detected = False
                    if self.all_channels_auto_reramp_box[mod_key][channel_key].checkState():
                        this_channel.auto_reramp_mode = "on"
                    else:
                        this_channel.auto_reramp_mode = "off"
          
        self.all_channels_time_between_trips_field[mod_key][channel_key].setPlaceholderText(str(this_channel.min_time_trips))        
        self.all_channels_set_voltage_field[mod_key][channel_key].setPlaceholderText(str(this_channel.set_voltage))
        self.all_channels_ramp_speed_field[mod_key][channel_key].setPlaceholderText(str(this_channel.ramp_speed))
        
        return
            
        
    def connect_hv_module(self, key, index):
        MainWindow.log.debug("connecting "+key)  
        com_port = self.module_com_line_edits[index].text().strip()
        self.modules[key].set_comport(com_port)
        is_high_precission = self.module_is_high_precission_boxes[index].checkState()
        self.modules[key].is_high_precission = is_high_precission
        
        try:
            self.modules[key].establish_connection()
            
        except FileNotFoundError:
            MainWindow.log.warning("Could not connect to HV Module: "
                   			"Wrong COM Port")
            self.err_msg_module = _qw.QMessageBox.warning(self, "HV module",
                                   	"Connection Failed! "
                                   	"Wrong Com port!")
            return
        # add here exception for com port in use!
        self.modules[key].sync_module()
        self.modules[key].read_module_info()
        self.module_com_line_edits[index].setDisabled(True)
        self.module_is_high_precission_boxes[index].setEnabled(False)
        self.module_connect_buttons[index].setEnabled(False)
        self.module_disconnect_buttons[index].setEnabled(True)        
        self.start_reader_thread(self.modules[key])
        return
        
    def disconnect_hv_module(self, key, index):
        MainWindow.log.debug("disconnecting "+key)  
        self.stop_reader_thread(self.modules[key])
        
        self.modules[key].close_connection()
        self.module_com_line_edits[index].setDisabled(False)      
        self.module_is_high_precission_boxes[index].setEnabled(True)        
        self.module_disconnect_buttons[index].setEnabled(False)        
        self.module_connect_buttons[index].setEnabled(True)
        return
        
    def start_reader_thread(self, module):
        if module.is_connected:
            module_thread = _thr.MonitorIsegModule(module)
            module.set_reader_thread(module_thread)
            module_thread.start()

    def stop_reader_thread(self, module):
        if not module.is_connected:
            return False
        module.stop_running_thread()      

        while module.board_occupied:
            MainWindow.log.debug("Waiting for thread "+module.name+" to stop")
            time.sleep(0.2)
        MainWindow.log.debug("thread "+module.name+" stopped")  
        
    def apply_hv_settings(self, module_key, channel_key):
        channel = self.channels[module_key][channel_key]
        if not self.modules[module_key].is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
        self.stop_reader_thread(self.modules[module_key])
        
        ramp_speed_text = self.all_channels_ramp_speed_field[module_key][channel_key].text().strip()
        set_voltage_text = self.all_channels_set_voltage_field[module_key][channel_key].text().strip()
        min_trip_time_text = self.all_channels_time_between_trips_field[module_key][channel_key].text().strip()

        try:
            if ramp_speed_text:
                ramp_speed = abs(int(float(ramp_speed_text)))
            else:
                ramp_speed = int(self.all_channels_ramp_speed_field[module_key][channel_key].placeholderText())
                
            if set_voltage_text:
                set_voltage = abs(int(float(set_voltage_text)))
            else:
                set_voltage = int(self.all_channels_set_voltage_field[module_key][channel_key].placeholderText())
                
            if min_trip_time_text:
                set_min_trip_time = abs(float(min_trip_time_text))
            else:
                set_min_trip_time = float(self.all_channels_time_between_trips_field[module_key][channel_key].placeholderText())

        except (ValueError, TypeError):
            self.err_msg_set_hv_values = _qw.QMessageBox.warning(self, "Values",
                                   	"Invalid input for the Board parameters!")
       	    self.start_reader_thread(self.modules[module_key])
            return False

        if channel.write_ramp_speed(ramp_speed):
            self.err_msg_set_hv_values_speed = _qw.QMessageBox.warning(self, "Set Ramp speed", 
            "Invalid response from HV Channel for set Ramp speed. Check values!")
            self.start_reader_thread(self.modules[module_key])
            return False
        if channel.write_set_voltage(set_voltage):
            self.err_msg_set_hv_values_voltage = _qw.QMessageBox.warning(self, "Set Voltage",
                           	"Invalid response from HV Channel for set Voltage. Check values!")
            self.start_reader_thread(self.modules[module_key])
            return False
        channel.min_time_trips = set_min_trip_time
        self.all_channels_ramp_speed_field[module_key][channel_key].setText("")
        self.all_channels_set_voltage_field[module_key][channel_key].setText("")
        self.all_channels_time_between_trips_field[module_key][channel_key].setText("")
        # This is neccessary to delete the current saved value and make the change clear
        channel.set_voltage = float('nan')
        channel.ramp_speed = float('nan')
        self.all_channels_ramp_speed_field[module_key][channel_key].setPlaceholderText("")
        self.all_channels_set_voltage_field[module_key][channel_key].setPlaceholderText("")
        self.all_channels_time_between_trips_field[module_key][channel_key].setPlaceholderText("")           
        self.start_reader_thread(self.modules[module_key])
        return True
        
    def start_hv_change(self, module_key, channel_key):
        if not self.modules[module_key].is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
            
        if _np.isnan(self.channels[module_key][channel_key].set_voltage) or _np.isnan(self.channels[module_key][channel_key].ramp_speed):
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Channel", 
                "Channel shows invalid value!")        
            return False
        if not self.interlock_value:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Interlock", 
                "Interlock is/was triggered! Abort Voltage change!")        
            return False

        confirmation = _qw.QMessageBox.question(self, "Are you sure?", 
        "You are about to ramp channel: "+self.channels[module_key][channel_key].name+
        "\nSet Voltage: "+str(self.channels[module_key][channel_key].set_voltage)+
        "\nRamp Speed: "+str(self.channels[module_key][channel_key].ramp_speed)+
        "\nPlease Confirm!", _qw.QMessageBox.Yes, _qw.QMessageBox.No)
        self.stop_reader_thread(self.modules[module_key])
        
        if confirmation == _qw.QMessageBox.Yes:
            answer = self.channels[module_key][channel_key].start_voltage_change()
            if not ("H2L" in answer or "L2H" in answer):
                self.err_msg_voltage_change = _qw.QMessageBox.warning(self, "Voltage Change",
               	"Invalid response from HV Channel. Check values!")
               	self.start_reader_thread(self.modules[module_key])
               	return False
            else:
                self.err_msg_voltage_change_good = _qw.QMessageBox.information(self, "Voltage Change",
                "Voltage is changing!")
                self.start_reader_thread(self.modules[module_key])
                return True
        else:
            self.err_msg_voltage_change_abort = _qw.QMessageBox.warning(self, "Voltage Change",
               	"Operation aborted!")
            self.start_reader_thread(self.modules[module_key])
            return False

    def _init_overview(self):
        MainWindow.log.debug("Called MainWindow._init_overview")
        self.hexe_drawing = _qw.QLabel()
        sketch_pixmap = _qg.QPixmap('hexesvm/icons/hexe_sketch_hv.svg')
        self.hexe_drawing.setPixmap(sketch_pixmap.scaledToHeight(self.frameGeometry().height()))

        self.channel_labels = []
        self.status_lights = []
        self.channel_voltage_lcds = []
        self.voltage_units = []
        self.channel_current_lcds = []
        self.current_units = []

        for pair in self.channel_order_dict:
        #for key, mod in self.channels.items():
            key = pair[1]
            self.channel_labels.append(_qw.QLabel(key))

            this_status_light = _qw.QLabel()
            gray_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_gray.svg')
            this_status_light.setPixmap(gray_dot_pixmap.scaledToHeight(48))
            self.status_lights.append(this_status_light)

            #this_voltage_lcd = _qw.QLabel()
            this_voltage_lcd = _qw.QLCDNumber()
            this_voltage_lcd.setNumDigits(5)
            this_voltage_lcd.setSegmentStyle(_qw.QLCDNumber.Flat)
            this_voltage_lcd.setAutoFillBackground(True)
            self.channel_voltage_lcds.append(this_voltage_lcd)

            self.voltage_units.append(_qw.QLabel('V'))

            #this_current_lcd = _qw.QLabel()
            this_current_lcd = _qw.QLCDNumber()
            this_current_lcd.setNumDigits(5)
            this_current_lcd.setSegmentStyle(_qw.QLCDNumber.Flat)
            this_current_lcd.setAutoFillBackground(True)
            self.channel_current_lcds.append(this_current_lcd)

            self.current_units.append(_qw.QLabel('µA'))

        status_label_text = _qw.QLabel('re-ramp')
        
        self.hv_kill_button = _qw.QPushButton('HV KILL')
        self.hv_kill_button.clicked.connect(self.kill_all_hv)
        self.hv_kill_button.setStyleSheet("QPushButton {background-color: red;}");
        
        grid_layout_y_positions = ((1,2,3,5,6))

        grid = _qw.QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self.hexe_drawing, 1,0,6,1)
        grid.addWidget(self.hv_kill_button, 0, 3)
        grid.addWidget(status_label_text, 0,6)

        #for i in range(len(self.channels)):
        for i in range(len(self.channel_order_dict)):        
            grid.addWidget(self.channel_labels[i], grid_layout_y_positions[i], 1)
            grid.addWidget(self.channel_voltage_lcds[i], grid_layout_y_positions[i], 2)
            grid.addWidget(self.voltage_units[i], grid_layout_y_positions[i], 3)
            grid.addWidget(self.channel_current_lcds[i], grid_layout_y_positions[i], 4)
            grid.addWidget(self.current_units[i], grid_layout_y_positions[i], 5)
            grid.addWidget(self.status_lights[i], grid_layout_y_positions[i], 6)

        self.overviewTab.setLayout(grid)

        self.update_overview()

    def update_overview(self):
        MainWindow.log.debug("Called MainWindow.update_overview")
        for i in range(len(self.channel_order_dict)):
        #for i, key in zip(range(len(self.channels)), self.channels.keys()):
            this_pair = self.channel_order_dict[i]

            #this_hv_channel = self.channels[key]
            this_hv_channel = self.channels[this_pair[0]][this_pair[1]]
            
            if _np.isnan(this_hv_channel.voltage):
                self.channel_voltage_lcds[i].display("Error")
                #self.channel_voltage_lcds[i].setText("Error")                
            else:
                self.channel_voltage_lcds[i].display(this_hv_channel.voltage)
                #self.channel_voltage_lcds[i].setText(str(this_hv_channel.voltage))

            current_value = this_hv_channel.current
            print(current_value)
            if this_hv_channel.module.is_high_precission:
                self.current_units[i].setText("nA")
                current_value = current_value*1E9
            else:
                self.current_units[i].setText("µA") 
                current_value = current_value*1E6
                               
            if _np.isnan(this_hv_channel.current):
                self.channel_current_lcds[i].display("Error")
                #self.channel_current_lcds[i].setText("Error")                
            else:
                self.channel_current_lcds[i].display(current_value)
                #self.channel_current_lcds[i].setText(str(current_value))
                
            palette = self.channel_voltage_lcds[i].palette()
            palette.setColor(palette.Background, _qg.QColor(10,10,10))
            if _np.isnan(this_hv_channel.voltage) or this_hv_channel.channel_is_tripped:
                palette.setColor(palette.WindowText, _qg.QColor(255,0,0))
            else:
                palette.setColor(palette.WindowText, _qg.QColor(0,255,0))
            self.channel_voltage_lcds[i].setPalette(palette)
            self.channel_current_lcds[i].setPalette(palette)

            if this_hv_channel.auto_reramp_mode == "on":
                green_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_green.svg')
                self.status_lights[i].setPixmap(green_dot_pixmap.scaledToHeight(48))
            elif this_hv_channel.auto_reramp_mode == "freq_trip":
                red_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_red.svg')
                self.status_lights[i].setPixmap(red_dot_pixmap.scaledToHeight(50))
            elif this_hv_channel.auto_reramp_mode == "no_dac":
                yellow_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_yellow.svg')
                self.status_lights[i].setPixmap(yellow_dot_pixmap.scaledToHeight(48))
            elif this_hv_channel.auto_reramp_mode == "off":
                gray_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_gray.svg')
                self.status_lights[i].setPixmap(gray_dot_pixmap.scaledToHeight(48))

             
        # if Db is connected, run the database insertion of these values
        if self.db_connection:
            self.insert_values_in_database()

        return

    def _init_settings(self):
        MainWindow.log.debug("Called _init_settings")
        # set main layout
        placeholder = _qw.QLabel(self.settingsTab)
        layout = _qw.QVBoxLayout()

        # add button
        self.sql_conn_button = _qw.QPushButton("connect")

        # add text forms and boxes
        form_layout = _qw.QFormLayout()

        self.form_address = _qw.QLineEdit(self.settingsTab)
        self.form_address.returnPressed.connect(self.sql_conn_button.click)
        self.form_db = _qw.QLineEdit(self.settingsTab)
        self.form_db.returnPressed.connect(self.sql_conn_button.click)
        self.form_tablename_hv = _qw.QLineEdit(self.settingsTab)
        self.form_tablename_hv.returnPressed.connect(self.sql_conn_button.click)
        self.form_tablename_interlock = _qw.QLineEdit(self.settingsTab)
        self.form_tablename_interlock.returnPressed.connect(self.sql_conn_button.click)
        self.form_user = _qw.QLineEdit(self.settingsTab)
        self.form_user.returnPressed.connect(self.sql_conn_button.click)
        self.form_password = _qw.QLineEdit(self.settingsTab)
        self.form_password.setEchoMode(_qw.QLineEdit.Password)
        self.form_password.returnPressed.connect(self.sql_conn_button.click)
        self.form_email = _qw.QLineEdit(self.settingsTab)
        self.form_email.returnPressed.connect(self.sql_conn_button.click)

        form_layout.addRow("address", self.form_address)
        form_layout.addRow("database name", self.form_db)
        form_layout.addRow("table name (HV)", self.form_tablename_hv)
        form_layout.addRow("table name (Interlock)", self.form_tablename_interlock)
        form_layout.addRow("user", self.form_user)
        form_layout.addRow("password", self.form_password)
        form_layout.addRow("Email recipient", self.form_email)       

        # connect button and set layout
        self.sql_conn_button.clicked.connect(self.sql_connect)
        layout.addLayout(form_layout)
        layout.addWidget(self.sql_conn_button)

        self.settingsTab.setLayout(layout)

        # set hexe_defaults
        self.set_hexe_defaults()

    def set_hexe_defaults(self):
        self.form_address.setText("lin-lxe")
        self.form_db.setText("postgres")
        self.form_tablename_hv.setText("hexe_sc_hv")
        self.form_tablename_interlock.setText("hexe_sc")
        self.form_user.setText("viewer")
        self.form_email.setText(self.email_sender.recipients)

    def sql_connect(self):

        """Connects to an SQL database by creating an SqlContainer instance"""
        MainWindow.log.debug("Called MainWindow.sql_connect")
        dialect = "postgresql"
        address = self.form_address.text().strip()
        dbname = self.form_db.text().strip()
        tablename = self.form_tablename_hv.text().strip()
        tablename_interlock = self.form_tablename_interlock.text().strip()
        username = self.form_user.text().strip()
        password = self.form_password.text().strip()
        # For now here....
        self.email_sender.set_mail_recipient(self.form_email.text().strip())

        try:

            self.sql_cont = _sql_writer(dialect, address, dbname,
                          tablename, username, password)

            self.sql_cont_interlock = _sql_writer(dialect, address, dbname,
                          tablename_interlock, username, password)


        except TypeError:
            MainWindow.log.warning("Could not connect to database: "
                   			"Missing parameters")
            self.err_msg = _qw.QMessageBox.warning(self, "SQL",
                                   	"Connection parameters "
                                   	"missing or invalid!")
            return
        except (_sql.exc.NoSuchTableError, _sql.exc.OperationalError):
            MainWindow.log.warning("Could not connect to database: "
                   	"Address, login credentials or"
                   	"database/table name invalid")
            self.err_msg = _qw.QMessageBox.warning(self, "SQL",
                                   "Address, login credentials "
                                   "or database/table name "
                                   "invalid!")
            return
        self.db_connection = True

        self.sql_conn_button.setEnabled(False)
        self.locker.set_sql_container(self.sql_cont_interlock)
        self.locker.set_interlock_parameter('p1', 0.052)
        
        
    def insert_values_in_database(self):

        MainWindow.log.debug("Called MainWindow.insert_values_in_database")
        cathode_voltage = self.channels["Drift module"]["Cathode"].voltage
        gate_voltage = self.channels["Drift module"]["Gate"].voltage
        anode_voltage = self.channels["Anode module"]["Anode"].voltage
        pmt_top_voltage = self.channels["PMT module"]["Top PMT"].voltage
        pmt_bot_voltage = self.channels["PMT module"]["Bottom PMT"].voltage        
        
        cathode_current = self.channels["Drift module"]["Cathode"].current
        gate_current = self.channels["Drift module"]["Gate"].current
        anode_current = self.channels["Anode module"]["Anode"].current
        pmt_top_current = self.channels["PMT module"]["Top PMT"].current
        pmt_bot_current = self.channels["PMT module"]["Bottom PMT"].current 

        current_datetime = _dt.now()

        insert_array = ([{"time": current_datetime, 
                          "u_anode": anode_voltage, 
                          "i_anode": anode_current, 
                          "u_gate": gate_voltage, 
                          "i_gate": gate_current, 
                          "u_cathode": cathode_voltage, 
                          "i_cathode": cathode_current,
                          "u_pmt_1": pmt_top_voltage,
                          "i_pmt_1": pmt_top_current,
                          "u_pmt_2": pmt_bot_voltage,
                          "i_pmt_2": pmt_bot_current},])
        
        try:
            self.sql_cont.write_values(insert_array)
            self.db_connection_write = True
            return True
            
        except _sql.exc.ProgrammingError:
        
            self.output_buffer_file.write(str(insert_array)+"\n")
            self.db_connection_write = False
            return False


    def send_mail(self, hv_channel, priority, alarm_mode):
        if self.email_sender.recipients == "":
            self.err_msg_mail = _qw.QMessageBox.warning(self, "Mail",
                                   "Set email recipient first!")
            return False
        
        self.email_sender.send_alarm(hv_channel, priority, alarm_mode)
        self.info_msg_mail = _qw.QMessageBox()
        self.info_msg_mail.setIcon(_qw.QMessageBox.Information)
        self.info_msg_mail.setText("Sent Email notification")
        self.info_msg_mail.setStandardButtons(_qw.QMessageBox.Ok)
        self.info_msg_mail.button(_qw.QMessageBox.Ok).animateClick(5000)
        self.info_msg_mail.exec_()
        return True

    def closeEvent(self, event):
        if not self.file_quit():
            event.ignore()

    def file_quit(self):
        """Closes the application"""
        MainWindow.log.debug("Called MainWindow.file_quit")


        reply = _qw.QMessageBox.question(self, 'Confirm',
	        'Are you sure to quit?', _qw.QMessageBox.Yes |
	        _qw.QMessageBox.No | _qw.QMessageBox.Cancel, 				
	        _qw.QMessageBox.Cancel)
        if reply == _qw.QMessageBox.Yes:
            self.close()
            return(True)
        else:
            return(False)

