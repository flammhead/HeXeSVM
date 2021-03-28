import sys
import os
import logging as _lg
import sqlalchemy as _sql
import numpy as _np
from datetime import datetime as _dt
import time
import json
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
from hexesvm.heartbeat_thread import HeartbeatSender as _hrtbt
from hexesvm import gui_hv_modules as _gui_hv

# create module logger
_gui_log = _lg.getLogger("hexesvm.gui")
_gui_log.setLevel(_lg.DEBUG)
_lg.debug("Loading hexesvm.gui")


class MainWindow(_qw.QMainWindow):

    log = _lg.getLogger("hexesvm.gui.MainWindow")

    def __init__(self):

        super().__init__()
        #_qw.QWidget.__init__(self)
        MainWindow.log.debug("Created MainWindow")

        # Loading the file with the default values
        with open("hexesvm/default_settings.json") as default_file:
                self.defaults = json.load(default_file)
        if not self.defaults:
                MainWindow.log.debug("Default value file not found!")

        # create the iSeg modules
        self._initialize_hv_modules()
        # create email notifier 
        self.email_sender = _mail.MailNotifier(self)
        # create interlocker
        self.locker = _interlock()
        self.locker.set_interlock_parameter(self.defaults['interlock_parameter'], 
                                            self.defaults['interlock_value'])        
        self.interlock_value = True
        # create database flag
        self.db_insertion_names = []
        self.db_connection = False
        self.db_connection_write = False
        self.output_buffer_file = open(self.defaults['temp_data_filename'], 'a')
        # create heartbeat sender
        self.heartbeat = _hrtbt(self)
        self.heartbeat.connect_socket()
        self.heartbeat.start()
        self.time_stamp = time.time()

        self.inAutoMode = False
        self.auto_ramp_thread = None

        self.timer = _qc.QTimer(self)
        self.timer.timeout.connect(self.updateUI)
        self.timer.start(1000)

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
        for module_tab in self.mod_tabs.values():
            module_tab.update_module_tab()
        # The current time stamp needs to be updated for the hearbeat detection
        self.time_stamp = time.time()

    def _initialize_hv_modules(self):		

        n_modules = len(self.defaults['modules'])

        self.modules = OrderedDict()
        self.channels = OrderedDict()
        index_list = [] # Helper dict for sorting later on
        for idx, this_module in enumerate(self.defaults['modules']):
           if this_module['type'] == "NHQ":
               self.modules.update({this_module['name']: _iseg.nhq_hv_module(this_module['name'], this_module['port'], this_module)})
           elif this_module['type'] == "NHR":
               self.modules.update({this_module['name']: _iseg.nhr_hv_module(this_module['name'], this_module['port'], this_module)})
           else:
              print("MODULE OF TYPE:", this_module['type'], " is not supported!!")
              continue
           this_mod_chan = OrderedDict()
           for jdx, this_channel in enumerate(this_module['channels']):
               this_mod_chan.update({this_channel['name']: self.modules[this_module['name']].add_channel(this_channel['index'], this_channel['name'], this_channel)})
               index_list.append([this_channel['img_pos'], this_module['name'], this_channel['name']])
           self.channels.update({this_module['name']: this_mod_chan})

        # Also construct one dict which holds the module/channel combination in the order
        # they should appear on the overview page
        self.channel_order_dict = []
        for i in range(len(index_list)):
           pos = -1
           for j in range(len(index_list)):
               if index_list[j][0] == i:
                   pos = j
           self.channel_order_dict.append((index_list[pos][1], index_list[pos][2]))

        
    def kill_all_hv(self):
        MainWindow.log.debug("Called KILL ALL HV method!")
        self.statusBar().showMessage("Called KILL ALL HV method!")
        response = []
        message = "High Voltage KILL was triggered and performed!\nModule responses:"        
        # stop any ramp plan that is executed.
        self.stop_ramp_schedule()
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

        # This will prevent from ramping HV up again
        self.interlock_value = False
        self.hv_kill_msg = _qw.QMessageBox()
        self.hv_kill_msg.setText(message)
        # window modality = 0 prevents the kill window to block the rest of the UI
        self.hv_kill_msg.setWindowModality(0);
        self.hv_kill_msg.show()
        #self.hv_kill_msg = _qw.QMessageBox.warning(self, "HV Kill", message)
        MainWindow.log.debug(response)
        
    def update_interlock(self):
        if not self.defaults['interlock_enabled']:
            self.locker.lock_state = True
            return
        # if too slow, the interlocker must be outsourced to an own thread?
        if not self.locker.is_running:
            self.locker.start()
        response = self.locker.lock_state
        if not response and self.locker.is_connected:
            if self.interlock_value:
                self.statusBar().showMessage("Interlock triggered: "+ str(self.locker.parameter_value))
                MainWindow.log.debug("Interlock triggered: "+ str(self.locker.parameter_value))
                self.kill_all_hv()
                self.locker.lock_state = False
                self.interlock_value = False

    def _init_geom(self):
        """Initializes the main window's geometry"""
        MainWindow.log.debug("Called MainWindow._init_geom")
        # set basic attributes
        self.setAttribute(_qc.Qt.WA_DeleteOnClose)
        self.setWindowTitle("HeXeSVM ("+str(self.defaults['version'])+")")
        self.resize(800, 400)

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
        sep_middle_1 = _qw.QLabel("")
        sep_middle_2 = _qw.QLabel("")
        sep_middle_1.setFrameStyle(_qw.QFrame.VLine)
        sep_middle_2.setFrameStyle(_qw.QFrame.VLine)        

        self.heartbeat_widget = _qw.QLabel("Heartbeat: ")
        self.heartbeat_widget.setToolTip("Indicates that the connection to the Watchdog is working")
        self.statusBar().addPermanentWidget(self.heartbeat_widget)
        self.statusBar().addPermanentWidget(sep_middle_1)
        self.interlock_widget = _qw.QLabel("Interlock: ")
        self.interlock_widget.setToolTip("Kills all HV if cryostat pressure below "+str(self.locker.lock_value)+" bara\n(Restart software to ramp up again!)")

        self.statusBar().addPermanentWidget(self.interlock_widget)
        self.statusBar().addPermanentWidget(sep_middle_2)
        self.database_widget = _qw.QLabel("Database: ")
        self.statusBar().addPermanentWidget(self.database_widget)
        self.update_status_bar()

    def update_status_bar(self):
    
        if self.heartbeat.connection_established:
            new_palette = self.heartbeat_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(0,204,0))
            self.heartbeat_widget.setPalette(new_palette)
            self.heartbeat_widget.setText("Heartbeat: OK")
            
        else:
            new_palette = self.heartbeat_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(255,0,0))
            self.heartbeat_widget.setPalette(new_palette)
            self.heartbeat_widget.setText("Heartbeat: FAILED!")                
        
        self.update_interlock()
        if self.defaults['interlock_enabled']:
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
        else:
            new_palette = self.interlock_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(255,0,0))
            self.interlock_widget.setPalette(new_palette)
            self.interlock_widget.setText("Interlock: DISABLED!")

        if self.db_connection_write:
            new_palette = self.database_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(0,204,0))
            self.database_widget.setPalette(new_palette)
            self.database_widget.setText("Database: OK")
            self.database_widget.setToolTip("HeXeSVM has write access to the dabase")
        else:
            new_palette = self.database_widget.palette()
            new_palette.setColor(_qg.QPalette.WindowText, _qg.QColor(255,0,0))
            self.database_widget.setPalette(new_palette)
            self.database_widget.setText("Database: ERROR")
            self.database_widget.setToolTip("Please connect to the database!\n(use writer account)")
        return


    def _init_subwindows(self):
        """Create the tabs"""
        MainWindow.log.debug("Called MainWindow._init_subwindows")
        self.main_widget = _qw.QTabWidget(self)
        self.setCentralWidget(self.main_widget)
        self.overviewTab = _qw.QWidget(self.main_widget)
        self.settingsTab = _qw.QWidget(self.main_widget)
        self.rampScheduleTab = _qw.QWidget(self.main_widget)
        self.main_widget.addTab(self.overviewTab, "Overview")
        # create tabs for the HV modules here
        self.mod_tabs = {}
        for key, mod in self.modules.items():
            if mod.type == "NHR":
                this_tab = _gui_hv.nhr_module_tab(self, self.defaults, mod)
                this_tab._init_module_tab()
                self.mod_tabs.update({key: this_tab})
                self.main_widget.addTab(this_tab, key)
            elif mod.type == "NHQ":
                this_tab = _gui_hv.nhq_module_tab(self, self.defaults, mod)
                this_tab._init_module_tab()
                self.mod_tabs.update({key: this_tab})
                self.main_widget.addTab(this_tab, key)
            else:
                MainWindow.log.debug("Called MainWindow._init_module_tabs: Non supported Module type required! "+mod.type)


        self.main_widget.addTab(self.rampScheduleTab, "Schedule")
        self.main_widget.addTab(self.settingsTab, "Settings")
		
        self._init_settings()
        self._init_ramp_schedule_tab()

        self._init_overview()

#TODO
    '''

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
        self.all_channels_single_sms_box = {}
        self.all_channels_frequent_button_group = {}
        self.all_channels_frequent_info_button = {}
        self.all_channels_frequent_alarm_button = {}
        self.all_channels_frequent_sms_box = {}
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
            self.all_channels_single_sms_box.update({key: {}})
            self.all_channels_frequent_button_group.update({key: {}})
            self.all_channels_frequent_info_button.update({key: {}})
            self.all_channels_frequent_alarm_button.update({key: {}})
            self.all_channels_frequent_sms_box.update({key: {}})
            self.all_channels_number_label.update({key: {}})
            self.all_channels_polarity_label.update({key: {}})
            self.all_channels_trip_detect_box.update({key: {}})
            self.all_channels_auto_reramp_box.update({key: {}})
            self.all_channels_time_between_trips_field.update({key: {}})
            self.all_channels_set_voltage_field.update({key: {}})
            self.all_channels_ramp_speed_field.update({key: {}})
            self.all_channels_apply_button.update({key: {}})
            self.all_channels_start_button.update({key: {}})



            # Create a tab for each channel in this moduel
            this_module_ch_tabs = _qw.QTabWidget(this_tab)
            this_module_ch_tabs.setTabPosition(_qw.QTabWidget.West)
            self.channel_tabs = {}
            self.channel_grids = []
            for idx in range(len(self.channels[key].keys())):
                this_channel_tab = _qw.QWidget(this_tab)
                # ADD to some list
                this_module_ch_tabs.addTab(this_channel_tab, key)
                # DO SOMETHING
                this_channel_grid = self._init_channel_section(key, list(self.channels[key].keys())[idx])
                self.channel_grids.append(this_channel_grid)
                this_channel_tab.setLayout(this_channel_grid)
                this_module_ch_tabs.addTab(this_channel_tab, list(self.channels[key].keys())[idx])

            grid.addWidget(this_module_ch_tabs, 5,1,8,6)
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
        this_channel_sms_settings_label = _qw.QLabel("sms")
        this_channel_single_button_group = _qw.QButtonGroup(this_tab)
        this_channel_single_none_button = _qw.QRadioButton()
        this_channel_single_button_group.addButton(this_channel_single_none_button, 0)                        
        this_channel_single_info_button = _qw.QRadioButton()
        this_channel_single_info_button.setChecked(True)
        this_channel_single_button_group.addButton(this_channel_single_info_button, 1)
        this_channel_single_alarm_button = _qw.QRadioButton()        
        this_channel_single_button_group.addButton(this_channel_single_alarm_button, 2)
        this_channel_single_sms_box = _qw.QCheckBox("", this_tab)
        self.all_channels_single_sms_box[mod_key].update({channel_key: this_channel_single_sms_box})
        self.all_channels_single_button_group[mod_key].update({channel_key: this_channel_single_button_group})
        this_channel_frequent_button_group = _qw.QButtonGroup(this_tab)               
        this_channel_frequent_none_button = _qw.QRadioButton()
        this_channel_frequent_button_group.addButton(this_channel_frequent_none_button, 0)                
        this_channel_frequent_info_button = _qw.QRadioButton()
        this_channel_frequent_button_group.addButton(this_channel_frequent_info_button, 1)        
        this_channel_frequent_alarm_button = _qw.QRadioButton()
        this_channel_frequent_alarm_button.setChecked(True)        
        this_channel_frequent_button_group.addButton(this_channel_frequent_alarm_button, 2) 
        this_channel_frequent_sms_box = _qw.QCheckBox("", this_tab)
        self.all_channels_frequent_sms_box[mod_key].update({channel_key: this_channel_frequent_sms_box})
        self.all_channels_frequent_button_group[mod_key].update({channel_key: this_channel_frequent_button_group})
        this_channel_single_test_button = _qw.QPushButton("test")
        this_channel_single_test_button.setToolTip("Send a test email for this event with the current settings")
        this_channel_frequent_test_button = _qw.QPushButton("test")
        this_channel_frequent_test_button.setToolTip("Send a test email for this event with the current settings")
        this_channel_single_test_button.clicked.connect(partial(self.send_mail, mod_key, channel_key, "single"))
        this_channel_frequent_test_button.clicked.connect(partial(self.send_mail, mod_key, channel_key, "frequent"))

        # separator for controls
        this_channel_vertical_separator = _qw.QLabel("")
        this_channel_vertical_separator.setFrameStyle(_qw.QFrame.VLine)
              
        # controls of the channel (right)
        this_channel_number_label =  _qw.QLabel('<span style="font-size:xx-large"><b>'+str(this_channel.channel)+'</b></span>')
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
        this_channel_time_between_trips_field.setToolTip("Minimum time between trips (minutes) for re-ramping.")
        self.all_channels_time_between_trips_field[mod_key].update({channel_key: this_channel_time_between_trips_field})
        this_channel_set_voltage_label = _qw.QLabel("Set voltage (V)")
        this_channel_set_voltage_field = _qw.QLineEdit(this_tab)
        self.all_channels_set_voltage_field[mod_key].update({channel_key: this_channel_set_voltage_field})
        this_channel_ramp_speed_label = _qw.QLabel("Ramp speed (V/s)")
        this_channel_ramp_speed_field = _qw.QLineEdit(this_tab)        
        self.all_channels_ramp_speed_field[mod_key].update({channel_key: this_channel_ramp_speed_field})
        this_channel_apply_button = _qw.QPushButton("apply")
        this_channel_apply_button.setToolTip("Write Set voltage and Ramp speed to the board. Refresh dT setting.\n(no voltage change will be triggered)")
        this_channel_apply_button.setFixedWidth(70)
        this_channel_apply_button.clicked.connect(partial(self.apply_hv_settings, mod_key, channel_key))
        self.all_channels_apply_button[mod_key].update({channel_key: this_channel_apply_button})
        # connect the return key to the apply action
        this_channel_time_between_trips_field.returnPressed.connect(this_channel_apply_button.click)
        this_channel_set_voltage_field.returnPressed.connect(this_channel_apply_button.click)
        this_channel_ramp_speed_field.returnPressed.connect(this_channel_apply_button.click)                
        
        this_channel_start_button = _qw.QPushButton("start")
        this_channel_start_button.setToolTip("Start voltage change of the board \n(using the currently set values)")
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
        grid.addWidget(this_channel_sms_settings_label, 10, 5, _qc.Qt.AlignLeft)
        grid.addWidget(this_channel_single_none_button, 11 , 2, _qc.Qt.AlignHCenter)      
        grid.addWidget(this_channel_single_info_button, 11, 3,_qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_single_alarm_button, 11, 4, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_single_sms_box, 11, 5, _qc.Qt.AlignLeft)
        grid.addWidget(this_channel_frequent_none_button, 12, 2, _qc.Qt.AlignHCenter)        
        grid.addWidget(this_channel_frequent_info_button, 12, 3, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_frequent_alarm_button, 12, 4, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_frequent_sms_box, 12, 5,  _qc.Qt.AlignLeft)
        grid.addWidget(this_channel_single_test_button, 11, 6, _qc.Qt.AlignHCenter)
        grid.addWidget(this_channel_frequent_test_button, 12, 6, _qc.Qt.AlignHCenter) 

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
        

        
    def update_channel_section(self, mod_key, channel_key):
        this_tab = self.mod_tabs[mod_key]
        this_channel = self.channels[mod_key][channel_key]
        
        none_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_gray_small.svg')
        ok_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_green_small.svg')
        err_pix = _qg.QPixmap('hexesvm/icons/hexe_circle_red_small.svg')
        
        if this_channel.channel_in_error is None:
            self.all_channels_error_sign[mod_key][channel_key].setPixmap(none_pix)
            self.all_channels_error_sign[mod_key][channel_key].setToolTip("Status not read")
        elif this_channel.channel_in_error is True:
            self.all_channels_error_sign[mod_key][channel_key].setPixmap(err_pix)
            self.all_channels_error_sign[mod_key][channel_key].setToolTip("HV quality not given")            
        elif this_channel.channel_in_error is False:
            self.all_channels_error_sign[mod_key][channel_key].setPixmap(ok_pix)
            self.all_channels_error_sign[mod_key][channel_key].setToolTip("HV quality ok")                        
            
        if this_channel.channel_is_tripped is None:
            self.all_channels_trip_sign[mod_key][channel_key].setPixmap(none_pix)
            self.all_channels_trip_sign[mod_key][channel_key].setToolTip("Status not read")            
        elif this_channel.channel_is_tripped is True:
            self.all_channels_trip_sign[mod_key][channel_key].setPixmap(err_pix)
            self.all_channels_trip_sign[mod_key][channel_key].setToolTip("Channel tripped!")                
        elif this_channel.channel_is_tripped is False:
            self.all_channels_trip_sign[mod_key][channel_key].setPixmap(ok_pix)
            self.all_channels_trip_sign[mod_key][channel_key].setToolTip("Channel not tripped!")                
            
        if this_channel.hardware_inhibit is None:
            self.all_channels_inhibit_sign[mod_key][channel_key].setPixmap(none_pix)
            self.all_channels_inhibit_sign[mod_key][channel_key].setToolTip("Status not read")            
        elif this_channel.hardware_inhibit is True:
            self.all_channels_inhibit_sign[mod_key][channel_key].setPixmap(err_pix)
            self.all_channels_inhibit_sign[mod_key][channel_key].setToolTip("Hardware inhibit is/was on!")
        elif this_channel.hardware_inhibit is False:
            self.all_channels_inhibit_sign[mod_key][channel_key].setPixmap(ok_pix)          
            self.all_channels_inhibit_sign[mod_key][channel_key].setToolTip("Hardware inhibit is off")
            
        if this_channel.kill_enable_switch is None:
            self.all_channels_kill_sign[mod_key][channel_key].setPixmap(none_pix)
            self.all_channels_kill_sign[mod_key][channel_key].setToolTip("Status not read")            
        elif this_channel.kill_enable_switch is False:
            self.all_channels_kill_sign[mod_key][channel_key].setPixmap(err_pix)
            self.all_channels_kill_sign[mod_key][channel_key].setToolTip("Kill switch disabled!")
        elif this_channel.kill_enable_switch is True:
            self.all_channels_kill_sign[mod_key][channel_key].setPixmap(ok_pix)
            self.all_channels_kill_sign[mod_key][channel_key].setToolTip("Kill switch enabeled")
            
            
        if this_channel.hv_switch_off is None:
            self.all_channels_hv_on_sign[mod_key][channel_key].setPixmap(none_pix)
            self.all_channels_hv_on_sign[mod_key][channel_key].setToolTip("Status not read")            
        elif this_channel.hv_switch_off is True:
            self.all_channels_hv_on_sign[mod_key][channel_key].setPixmap(err_pix)
            self.all_channels_hv_on_sign[mod_key][channel_key].setToolTip("HV switch is off!")
        elif this_channel.hv_switch_off is False:
            self.all_channels_hv_on_sign[mod_key][channel_key].setPixmap(ok_pix)
            self.all_channels_hv_on_sign[mod_key][channel_key].setToolTip("HV is on")
            
        if this_channel.manual_control is None:
            self.all_channels_dac_on_sign[mod_key][channel_key].setPixmap(none_pix)
            self.all_channels_dac_on_sign[mod_key][channel_key].setToolTip("Status not read")            
        elif this_channel.manual_control is True:
            self.all_channels_dac_on_sign[mod_key][channel_key].setPixmap(err_pix)
            self.all_channels_dac_on_sign[mod_key][channel_key].setToolTip("Board is in manual control mode!")            
        elif this_channel.manual_control is False:
            self.all_channels_dac_on_sign[mod_key][channel_key].setPixmap(ok_pix)
            self.all_channels_dac_on_sign[mod_key][channel_key].setToolTip("Board is in remote control mode")                        
        
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
        self.all_channels_trip_rate_field[mod_key][channel_key].setToolTip("Trips for this channel in the last 24 hours")
        
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


    @_qc.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject')    
    def apply_hv_settings(self, module_key, channel_key):
        channel = self.channels[module_key][channel_key]
        if not self.modules[module_key].is_connected:
            self.err_msg_set_module_no_conn = _qw.QMessageBox.warning(self, "Module", 
                "Module is not connected!")
            return False
        self.stop_reader_thread(self.modules[module_key])
        while self.modules[module_key].board_occupied:
            time.sleep(0.2)
        self.modules[module_key].board_occupied = True
        
        ramp_speed_text = self.all_channels_ramp_speed_field[module_key][channel_key].text().strip()
        set_voltage_text = self.all_channels_set_voltage_field[module_key][channel_key].text().strip()
        min_trip_time_text = self.all_channels_time_between_trips_field[module_key][channel_key].text().strip()
        print("try")
        try:
            if ramp_speed_text:
                ramp_speed = abs(int(float(ramp_speed_text)))
            else:
                ramp_speed = int(float(self.all_channels_ramp_speed_field[module_key][channel_key].placeholderText()))
                
            if set_voltage_text:
                set_voltage = abs(int(float(set_voltage_text)))
            else:
                set_voltage = int(float(self.all_channels_set_voltage_field[module_key][channel_key].placeholderText()))
                
            if min_trip_time_text:
                set_min_trip_time = abs(float(min_trip_time_text))
            else:
                set_min_trip_time = float(self.all_channels_time_between_trips_field[module_key][channel_key].placeholderText())

        except (ValueError, TypeError):
            self.err_msg_set_hv_values = _qw.QMessageBox.warning(self, "Values",
            "Invalid input for the Board parameters!")
            self.modules[module_key].board_occupied = False
       	    self.start_reader_thread(self.modules[module_key])
            return False

        if channel.write_ramp_speed(ramp_speed):
            self.err_msg_set_hv_values_speed = _qw.QMessageBox.warning(self, "Set Ramp speed", 
            "Invalid response from HV Channel for set Ramp speed. Check values!")
            self.modules[module_key].board_occupied = False            
            self.start_reader_thread(self.modules[module_key])
            return False
        if channel.write_set_voltage(set_voltage):
            self.err_msg_set_hv_values_voltage = _qw.QMessageBox.warning(self, "Set Voltage",
                           	"Invalid response from HV Channel for set Voltage. Check values!")
            self.modules[module_key].board_occupied = False
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
#TODO

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
        self.hv_kill_button.setToolTip("Ramp down all channels (@255V/s)\n(Restart software to ramp up again!)")
        #self.hv_kill_button.setToolTip("Clicking will trigger all connected modules to ramp to 0V (at 255 V/s).\nRamping back up requires restart of the software.")
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
        #MainWindow.log.debug("Called MainWindow.update_overview")
        for i in range(len(self.channel_order_dict)):
        #for i, key in zip(range(len(self.channels)), self.channels.keys()):
            this_pair = self.channel_order_dict[i]

            #this_hv_channel = self.channels[key]
            this_hv_channel = self.channels[this_pair[0]][this_pair[1]]
            
            if _np.isnan(this_hv_channel.voltage):
                self.channel_voltage_lcds[i].display("Error")
                self.channel_voltage_lcds[i].setToolTip("Please connect the HV module!")
                #self.channel_voltage_lcds[i].setText("Error")                
            else:
                self.channel_voltage_lcds[i].display(this_hv_channel.voltage)
                self.channel_voltage_lcds[i].setToolTip("Actual voltage of the channel")                
                #self.channel_voltage_lcds[i].setText(str(this_hv_channel.voltage))

            current_value = this_hv_channel.current
            if this_hv_channel.module.is_high_precission or this_hv_channel.module.type == "NHR":
                self.current_units[i].setText("nA")
                current_value = current_value*1E9
            else:
                self.current_units[i].setText("µA") 
                current_value = current_value*1E6
                               
            if _np.isnan(this_hv_channel.current):
                self.channel_current_lcds[i].display("Error")
                self.channel_current_lcds[i].setToolTip("Please connect the HV module!")                
                #self.channel_current_lcds[i].setText("Error")                
            else:
                self.channel_current_lcds[i].display(current_value)
                self.channel_current_lcds[i].setToolTip("Actual current of the channel")                                
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
                self.status_lights[i].setToolTip("Re-ramp is running")                
                self.status_lights[i].setPixmap(green_dot_pixmap.scaledToHeight(48))
            elif this_hv_channel.auto_reramp_mode == "freq_trip":
                red_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_red.svg')
                self.status_lights[i].setToolTip("Frequent tripping deteced.\nRe-ramp disabeled!")                
                self.status_lights[i].setPixmap(red_dot_pixmap.scaledToHeight(48))
            elif this_hv_channel.auto_reramp_mode == "no_dac":
                yellow_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_yellow.svg')
                self.status_lights[i].setToolTip("DAC switch of channel is off!")                
                self.status_lights[i].setPixmap(yellow_dot_pixmap.scaledToHeight(48))
            elif this_hv_channel.auto_reramp_mode == "off":
                gray_dot_pixmap = _qg.QPixmap('hexesvm/icons/hexe_circle_gray.svg')
                self.status_lights[i].setToolTip("Re-ramp is switched off!")                
                self.status_lights[i].setPixmap(gray_dot_pixmap.scaledToHeight(48))

             
        # if Db is connected, run the database insertion of these values
        if self.db_connection:
            self.insert_values_in_database()

        return
        
    def _init_ramp_schedule_tab(self):
        """This section contains the tab in which the user can load and 
        Manage a predifened ramping plan"""
        MainWindow.log.debug("Called _init_ramp_schedule_tab")
        grid = _qw.QGridLayout()
        grid.setSpacing(10)
        
        self.rampTable_heading = _qw.QLabel("This table can be used to set up scheduled ramping procedure")
        self.rampTable = _qw.QTableWidget(self.rampScheduleTab)
        self.rampTable.setRowCount(0)
        # For now, the table is not edit, to be safe... might be changed at some point
        self.rampTable.setEditTriggers(_qw.QAbstractItemView.NoEditTriggers)
        self.rampTable.setColumnCount(len(self.channel_order_dict*2)+1)
        list_header = []
        for i in range(len(self.channel_order_dict)):
            list_header.append("U("+self.channel_order_dict[i][1]+")")
            list_header.append("V("+self.channel_order_dict[i][1]+")")
        
        self.rampTable.setHorizontalHeaderLabels(["time"] + list_header)
        self.rampTable.verticalHeader().setVisible(False)
        self.rampTable.resizeColumnsToContents()
        
        
        self.rampTableLoadButton = _qw.QPushButton("&Load")
        self.rampTableLoadButton.clicked.connect(self.load_ramp_schedule)
        self.rampTableSaveButton = _qw.QPushButton("&Save")
        self.rampTableSaveButton.clicked.connect(self.save_ramp_schedule)        
        self.rampTableRunButton = _qw.QPushButton("Run")
        self.rampTableRunButton.clicked.connect(self.run_ramp_schedule)
        self.rampTableRunButton.setStyleSheet("QPushButton {background-color: green;}")     
        self.rampTableStopButton = _qw.QPushButton("Stop")
        self.rampTableStopButton.clicked.connect(self.stop_ramp_schedule)
        self.rampTableStopButton.setEnabled(False)
        self.rampTableStopButton.setStyleSheet("QPushButton {background-color: red;}")      

        #y,x (order for the grid)
        grid.addWidget(self.rampTable_heading, 1,1, 1,6)
        grid.addWidget(self.rampTable, 2,1,4,6)
        grid.addWidget(self.rampTableLoadButton, 6,3)
        grid.addWidget(self.rampTableSaveButton, 6,2)
        grid.addWidget(self.rampTableRunButton, 6,4)
        grid.addWidget(self.rampTableStopButton, 6,5)

        self.rampScheduleTab.setLayout(grid)
    
    def load_ramp_schedule(self):
        dialog = _qw.QFileDialog()
        dialog.setFileMode(_qw.QFileDialog.ExistingFile)
        dialog.setDirectory(os.path.join("hexesvm","etc"))
        filename = ""
        data = []
        if dialog.exec_():
            filename = dialog.selectedFiles()
            with open(filename[0], "r") as f_in:
                lines = f_in.read()
                lines = lines.split("\n")
                for line in lines:
                    line = line.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t','')
                    if line:
                        if line[0] == '#':
                            continue
                        this_elements = line.split(",")
                        data.append(this_elements)
                    
            # Validate the data!
            length = self.rampTable.columnCount()
            for row in data:
                if len(row) != length:
                    print("Loaded Data has missing (too little) values!")
                    return False
            try:
                data_np = _np.asarray(data, dtype=_np.float32)
            except ValueError:
                print("Loaded Data is not of correct type!")
                return False
            # check if the table does not proceed too far in the future.
            if _np.sum(data_np[:,0]) >= 96.*60.:
                print("Loaded Data is going too far in the future!!")
                return False
            if _np.min(data_np[1:,0]) < 1.:
                print("Loaded Data contains a time intervall < 1 minute!")
            #clear previous data content
            self.rampTable.setRowCount(0)
            self.rampTable.setRowCount(data_np.shape[0])
            for i in range(data_np.shape[0]):
                for j in range(data_np.shape[1]):
                    newTableItem = _qw.QTableWidgetItem(str(data_np[i,j]))
                    self.rampTable.setItem(i,j, newTableItem)
            self.tampTableDataNp = data_np  
            self.rampTable.resizeColumnsToContents()

    def save_ramp_schedule(self):
        dialog = _qw.QFileDialog()
        dialog.setFileMode(_qw.QFileDialog.AnyFile)
        dialog.setAcceptMode(_qw.QFileDialog.AcceptSave)
        dialog.setDirectory(os.path.join("hexesvm","etc"))
        filename = ""
        if dialog.exec_():
            filename = dialog.selectedFiles()
            with open(filename[0], "w") as f_out:
                f_out.write('#')
                for j in range(self.rampTable.columnCount()):
                    f_out.write(self.rampTable.horizontalHeaderItem(j).text())
                    if j <= self.rampTable.columnCount():
                        f_out.write(',')
                f_out.write('\n')
                for i in range(self.rampTable.rowCount()):
                    for j in range(self.rampTable.columnCount()):
                        this_item = self.rampTable.itemAt(i,j)
                        f_out.write(str(self.rampTable.item(i,j).text()))
                        if j <= self.rampTable.columnCount():
                            f_out.write(',')
                    f_out.write('\n')
                        

    def run_ramp_schedule(self):

        if self.rampTable.rowCount() < 1:
            print("No data in the ramp schedule!")
            return False
        #if not self.locker.lock_state:
        if not self.locker.lock_state:        
            print("Interlock is triggered!")
            return False
        self.inAutoMode = True

        for mod_key, channel_key in self.channel_order_dict:
            self.all_channels_apply_button[mod_key][channel_key].setEnabled(False)
            self.all_channels_start_button[mod_key][channel_key].setEnabled(False)
            self.all_channels_ramp_speed_field[mod_key][channel_key].setDisabled(True)
            self.all_channels_set_voltage_field[mod_key][channel_key].setDisabled(True)
            self.all_channels_time_between_trips_field[mod_key][channel_key].setDisabled(True)

        self.rampTableRunButton.setEnabled(False)        
        self.rampTableStopButton.setEnabled(True)
        
        #start the auto ramp thread
        self.auto_ramp_thread = _thr.ScheduleRampIsegModule(self)
        # connect thread's signals to the respective apply and ramp functions

        self.auto_ramp_thread.highlight_row.connect(self.highlight_ramp_table_row)
        self.auto_ramp_thread.change_hv_settings.connect(self.change_channel_hv_field)
        self.auto_ramp_thread.apply_hv.connect(self.apply_hv_settings)
        self.auto_ramp_thread.ramp_hv.connect(self.start_hv_change)
        self.auto_ramp_thread.finished.connect(self.stop_ramp_schedule)

        self.auto_ramp_thread.start()        

             
        return

    def stop_ramp_schedule(self):

        if not self.inAutoMode:
            return
	    #disconnect the threads signals
        #self.auto_ramp_thread.apply_hv.disconnect()
        #self.auto_ramp_thread.ramp_hv.disconnect()
        #self.auto_ramp_thread.highlight_row.disconnect()
        #self.auto_ramp_thread.change_hv_settings.disconnect()

        # stop the auto ramp thread
        self.auto_ramp_thread.stop()
        # and wait until it is shut down
        #while self.auto_ramp_thread.is_running:
        #    print("Waiting for ramp table thread to stop")
        #    time.sleep(0.2)
        self.auto_ramp_thread = None

        for i in range(self.rampTable.rowCount()):
            for j in range(self.rampTable.columnCount()):
                self.rampTable.item(i, j).setBackground(_qg.QColor(255,255,255))       
        self.rampTableCurrentIndex = 0
        
        self.rampTableRunButton.setEnabled(True)        
        self.rampTableStopButton.setEnabled(False)
        for mod_key, channel_key in self.channel_order_dict:
            self.all_channels_apply_button[mod_key][channel_key].setEnabled(True)
            self.all_channels_start_button[mod_key][channel_key].setEnabled(True)
            self.all_channels_ramp_speed_field[mod_key][channel_key].setDisabled(False)
            self.all_channels_set_voltage_field[mod_key][channel_key].setDisabled(False)
            self.all_channels_time_between_trips_field[mod_key][channel_key].setDisabled(False)            
        self.inAutoMode = False

        return

    @_qc.pyqtSlot('PyQt_PyObject')      
    def highlight_ramp_table_row(self, idx):

        for i in range(self.rampTable.columnCount()):
            if not (idx == 0):
                self.rampTable.item(idx-1, i).setBackground(_qg.QColor(255,255,255))             
            self.rampTable.item(idx, i).setBackground(_qg.QColor(195, 247, 204))
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
        self.form_email_info = _qw.QLineEdit(self.settingsTab)
        self.form_email_info.returnPressed.connect(self.sql_conn_button.click)
        self.form_email_alarm = _qw.QLineEdit(self.settingsTab)
        self.form_email_alarm.returnPressed.connect(self.sql_conn_button.click)
        self.form_email_sms = _qw.QLineEdit(self.settingsTab)
        self.form_email_sms.returnPressed.connect(self.sql_conn_button.click)
        
        self.interlock_line_edit_par = _qw.QLineEdit(self.settingsTab)
        self.interlock_line_edit_par.setText(str(self.locker.lock_param))
        self.interlock_line_edit_par.setDisabled(True)
        self.interlock_line_edit_val = _qw.QLineEdit(self.settingsTab)
        self.interlock_line_edit_val.setText(str(self.locker.lock_value))
        self.interlock_line_edit_val.setDisabled(True)


        form_layout.addRow("address", self.form_address)
        form_layout.addRow("database name", self.form_db)
        form_layout.addRow("table name (HV)", self.form_tablename_hv)
        form_layout.addRow("table name (Interlock)", self.form_tablename_interlock)
        form_layout.addRow("user", self.form_user)
        form_layout.addRow("password", self.form_password)
        form_layout.addRow("Email recipient (info)", self.form_email_info)       
        form_layout.addRow("Email recipient (alarm)", self.form_email_alarm)       
        form_layout.addRow("SMS recipients", self.form_email_sms)
        
        form_layout.addRow("Interlock parameter", self.interlock_line_edit_par)
        form_layout.addRow("Lock Value", self.interlock_line_edit_val)        

        # connect button and set layout
        self.sql_conn_button.clicked.connect(self.sql_connect)
        layout.addLayout(form_layout)
        layout.addWidget(self.sql_conn_button)

        self.settingsTab.setLayout(layout)

        # set hexe_defaults
        self.set_hexe_defaults()

    def set_hexe_defaults(self):
        self.form_address.setText(self.defaults['db_address'])
        self.form_db.setText(self.defaults['db_type'])
        self.form_tablename_hv.setText(self.defaults['table_name'])
        self.form_tablename_interlock.setText(self.defaults['interlock_table_name'])
        self.form_user.setText(self.defaults['db_user_name'])
        self.form_email_info.setText(self.email_sender.recipients_info)
        self.form_email_alarm.setText(self.email_sender.recipients_alarm)
        self.form_email_sms.setText(self.email_sender.sms_numbers)

    def sql_connect(self):

        """Connects to an SQL database by creating an SqlContainer instance"""
        MainWindow.log.debug("Called MainWindow.sql_connect")
        self.statusBar().showMessage("connecting sql")
        dialect = "postgresql"
        address = self.form_address.text().strip()
        dbname = self.form_db.text().strip()
        tablename = self.form_tablename_hv.text().strip()
        tablename_interlock = self.form_tablename_interlock.text().strip()
        username = self.form_user.text().strip()
        password = self.form_password.text().strip()
        # For now here....
        self.email_sender.set_mail_recipient_info(self.form_email_info.text().strip())
        self.email_sender.set_mail_recipient_alarm(self.form_email_alarm.text().strip())
        self.email_sender.set_sms_recipient(self.form_email_sms.text().strip())

        try:

            self.sql_cont = _sql_writer(dialect, address, dbname,
                          tablename, username, password)

            self.sql_cont_interlock = _sql_writer(dialect, address, dbname,
                          tablename_interlock, username, password)


        except TypeError:
            MainWindow.log.warning("Could not connect to database: "
                   			"Missing parameters")
            self.statusBar().showMessage("error while connecting slq")
            self.err_msg = _qw.QMessageBox.warning(self, "SQL",
                                   	"Connection parameters "
                                   	"missing or invalid!")
            return
        except (_sql.exc.NoSuchTableError, _sql.exc.OperationalError):
            MainWindow.log.warning("Could not connect to database: "
                   	"Address, login credentials or"
                   	"database/table name invalid")
            self.statusBar().showMessage("error while connecting slq")
            self.err_msg = _qw.QMessageBox.warning(self, "SQL",
                                   "Address, login credentials "
                                   "or database/table name "
                                   "invalid!")
            return
        self.db_connection = True
        self.statusBar().showMessage("sql connection established")
        self.sql_conn_button.setEnabled(False)
        #self.locker.set_sql_container(self.sql_cont_interlock)
        self.locker.set_psycopg_conn(address, dbname, username, password, tablename_interlock)
        
        # Also read from the settings file the db_insertion names for the moduels
        for idx, this_module in enumerate(self.defaults['modules']):
           for jdx, this_channel in enumerate(this_module['channels']):
                # see if this channel has a db tag in the settings file
                try:
                    this_db_tag_voltage = this_channel['db_u_name']
                    this_db_tag_current = this_channel['db_i_name']
                    self.db_insertion_names.append([this_module['name'], this_channel['name'], this_db_tag_voltage, this_db_tag_current])
                except KeyError:
                    # This channel does not have a db identifier, so we can't add it
                    # to the insertion array
                    print("No Database identifier for:", this_channel)        
        
        
    def insert_values_in_database(self):

        current_datetime = _dt.now()

        # inizialize empty dict, which will hold the pairs of SQL field names
        # and respective values
        insert_array = {}
        insert_array["time"] = current_datetime

        for this_insertion in self.db_insertion_names:
            this_voltage = self.channels[this_insertion[0]][this_insertion[1]].voltage
            this_current = self.channels[this_insertion[0]][this_insertion[1]].current
            insert_array[this_insertion[2]] = this_voltage
            insert_array[this_insertion[3]] = this_current
        
        try:
            self.sql_cont.write_values(insert_array)
            self.db_connection_write = True
            return True
            
        except _sql.exc.ProgrammingError:
        
            self.output_buffer_file.write(str(insert_array)+"\n")
            self.db_connection_write = False
            return False


    def send_mail(self, mod_key, channel_key, alarm_mode):

        if self.email_sender.recipients_info == "" or self.email_sender.recipients_alarm == "":
            self.err_msg_mail = _qw.QMessageBox.warning(self, "Mail",
                                   "Set info & and alarm email recipients first!")
            return False
        if alarm_mode == "single":
            sms_flag = self.all_channels_single_sms_box[mod_key][channel_key].checkState()
            priority = self.all_channels_single_button_group[mod_key][channel_key].checkedId()
        elif alarm_mode == "frequent":
            sms_flag = self.all_channels_frequent_sms_box[mod_key][channel_key].checkState()
            priority = self.all_channels_frequent_button_group[mod_key][channel_key].checkedId()

        hv_channel = self.channels[mod_key][channel_key]
        self.email_sender.send_alarm(hv_channel, priority, alarm_mode)
        if sms_flag:
            self.email_sender.send_sms(hv_channel, priority, alarm_mode)
        self.info_msg_mail = _qw.QMessageBox()
        self.info_msg_mail.setIcon(_qw.QMessageBox.Information)
        self.info_msg_mail.setText("Sent Email notification")
        self.info_msg_mail.setStandardButtons(_qw.QMessageBox.Ok)
        self.info_msg_mail.button(_qw.QMessageBox.Ok).animateClick(2000)
        self.info_msg_mail.exec_()
        return True
	
    
    def file_quit(self):
        """Closes the application"""
        MainWindow.log.debug("Called MainWindow.file_quit")
        self.statusBar().showMessage("Quitting application")

        reply = _qw.QMessageBox.question(self, 'Confirm',
	        'Are you sure to quit?', _qw.QMessageBox.Yes |
	        _qw.QMessageBox.No | _qw.QMessageBox.Cancel, 				
	        _qw.QMessageBox.Cancel)
        if reply == _qw.QMessageBox.Yes:
            # Disconnect the modules
            for i, key in zip(range(len(self.modules)), self.modules.keys()):
                if self.modules[key].is_connected:
                    self.disconnect_hv_module(key, i)
            self.close()
            return(True)
        else:
            return(False)

