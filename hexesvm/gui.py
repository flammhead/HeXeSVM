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
        # create interlocker
        self.locker = _interlock()
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
        

    def _initialize_hv_modules(self):		

        self.modules = OrderedDict(
        {"PMT module": _iseg.hv_module("pmt module", "COM7"),
        "Anode module": _iseg.hv_module("anode module", "COM17"),
        "Drift module": _iseg.hv_module("drift module", "COM18")})		        
				        
        self.channels = OrderedDict(
        {"Top PMT": self.modules["PMT module"].add_channel(1, "top pmt"),
        "Anode": self.modules["Anode module"].add_channel(2, "anode"),
        "Gate": self.modules["Drift module"].add_channel(2, "gate"),
        "Cathode": self.modules["Drift module"].add_channel(1, "cathode"),
        "Bottom PMT": self.modules["PMT module"].add_channel(2, "bottom pmt")})
        
    def kill_all_hv(self):
        MainWindow.log.debug("Called KILL ALL HV method!")
        response = []
        message = "High Voltage KILL was triggered and performed!\nModule responses:"
        # Tell the threads of all modules to terminate
        for key in self.modules.keys():
            if not self.modules[key].is_connected:
                continue
            self.modules[key].stop_running_thread()      

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
        self.interlock_value = self.locker.check_interlock()
        if not self.interlock_value and self.db_connection:
            self.kill_all_hv()

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


    def _init_subwindows(self):
        """Create the tabs"""
        MainWindow.log.debug("Called MainWindow._init_subwindows")
        self.main_widget = _qw.QTabWidget(self)
        self.setCentralWidget(self.main_widget)
        self.overviewTab = _qw.QWidget(self.main_widget)
        self.settingsTab = _qw.QWidget(self.main_widget)
        self.main_widget.addTab(self.overviewTab, "Overview")
        # create tabs for the HV modules here
        self.mod_tabs = []
        for key, mod in self.modules.items():
            this_tab = _qw.QWidget(self.main_widget)
            self.mod_tabs.append(this_tab)
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
        
        MainWindow.log.debug("Called MainWindow._init_module_tabs")
        for i, key in zip(range(len(self.modules)), self.modules.keys()):

            this_tab = self.mod_tabs[i]
            this_module = self.modules[key]
            this_modules_channels = this_module.child_channels
    
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
            self.module_umax_fields.append(this_u_max_label)
            
            this_i_max_label = _qw.QLabel("I(mA):")
            self.module_imax_labels.append(this_i_max_label)
            this_i_max_field = _qw.QLineEdit(this_tab)
            this_i_max_field.setDisabled(True)
            self.module_imax_fields.append(this_i_max_label)            

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
            vertical_separator = _qw.QLabel("")
            vertical_separator.setFrameStyle(_qw.QFrame.VLine)
        
            grid = _qw.QGridLayout()
            grid.setSpacing(10)
            # Row 1 widgetd
            grid.addWidget(this_com_port_label, 1,2)
            grid.addWidget(this_com_port, 1,3,1,2)
            grid.addWidget(this_high_precision_label, 1, 7)
            grid.addWidget(this_high_precision_box, 1,8)
            # Row 2 widgets
            grid.addWidget(this_connect_button, 2,2, 1,2)
            grid.addWidget(this_disconnect_button, 2,7, 1,2)            
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
            

            channel_grid = self._init_channel_section(i, this_modules_channels[0])
            grid.addLayout(channel_grid, 5,1, 8,3)
            grid.addWidget(vertical_separator, 5, 5, 8, 1)
            this_tab.setLayout(grid)
            
            self.module_grid_layouts.append(grid)           

        return

    def _init_channel_section(self, mod_index, channel):
        this_tab = self.mod_tabs[mod_index]
        #this_channel = self.channels[channel_key]
        this_channel = channel
        
        this_channel_name_label = _qw.QLabel(this_channel.name)
        
        this_channel_error_label = _qw.QLabel("Error")
        this_channel_error_sign = _qw.QLabel()
        this_channel_error_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_circle_red_small.svg'))

        this_channel_trip_label = _qw.QLabel("Trip")
        this_channel_trip_sign = _qw.QLabel()
        this_channel_trip_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_circle_green_small.svg'))
        
        this_channel_inhibit_label = _qw.QLabel("Inhibit")
        this_channel_inhibit_sign = _qw.QLabel()
        this_channel_inhibit_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_circle_gray_small.svg'))
        
        this_channel_kill_label = _qw.QLabel("Kill")
        this_channel_kill_sign = _qw.QLabel()
        this_channel_kill_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_circle_gray_small.svg'))
        
        this_channel_hv_on_label = _qw.QLabel("HV on")
        this_channel_hv_on_sign = _qw.QLabel()
        this_channel_hv_on_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_circle_gray_small.svg'))
        
        this_channel_dac_on_label = _qw.QLabel("DAC on")
        this_channel_dac_on_sign = _qw.QLabel()
        this_channel_dac_on_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_arrow_up.svg'))
        
        this_channel_hv_ramp_label = _qw.QLabel("HV ramp")
        this_channel_hv_ramp_sign = _qw.QLabel()
        this_channel_hv_ramp_sign.setPixmap(_qg.QPixmap('hexesvm/hexe_arrow_down.svg'))
        
        this_channel_trip_rate_label = _qw.QLabel("Trips")
        this_channel_trip_rate_field = _qw.QLineEdit(this_tab)
        this_channel_trip_rate_field.setText("0 per 24hr")
        this_channel_trip_rate_field.setDisabled(True)
        
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

        
        return grid
        
        
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
        self.module_connect_buttons[index].setEnabled(False)
        self.module_disconnect_buttons[index].setEnabled(True)        
        self.start_reader_thread(self.modules[key])
        return
        
    def disconnect_hv_module(self, key, index):
        MainWindow.log.debug("disconnecting "+key)  
        if not self.modules[key].is_connected:
            return
        self.modules[key].stop_running_thread()      

        while self.modules[key].board_occupied:
            MainWindow.log.debug("Waiting for thread "+key+" to stop"+str(self.modules[key].stop_thread))
            time.sleep(0.2)
        MainWindow.log.debug("thread "+key+" stopped")  
        
        self.modules[key].close_connection()                
        self.module_disconnect_buttons[index].setEnabled(False)        
        self.module_connect_buttons[index].setEnabled(True)
        return
        
    def start_reader_thread(self, module):
        if module.is_connected:
            module_thread = _thr.MonitorIsegModule(module)
            module.set_reader_thread(module_thread)
            module_thread.start()


    def _init_overview(self):
        MainWindow.log.debug("Called MainWindow._init_overview")
        self.hexe_drawing = _qw.QLabel()
        self.hexe_drawing.setPixmap(_qg.QPixmap('hexesvm/hexe_sketch_hv.svg'))

        self.channel_labels = []
        self.status_lights = []
        self.channel_voltage_lcds = []
        self.voltage_units = []
        self.channel_current_lcds = []
        self.current_units = []

        for key, mod in self.channels.items():
            self.channel_labels.append(_qw.QLabel(key))

            this_status_light = _qw.QLabel()
            this_status_light.setPixmap(_qg.QPixmap('hexesvm/hexe_circle_gray.svg'))
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

        for i in range(len(self.channels)):
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
        for i, key in zip(range(len(self.channels)), self.channels.keys()):

            this_hv_channel = self.channels[key]
            
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
            if this_hv_channel.channel_in_error or this_hv_channel.channel_is_tripped:
                palette.setColor(palette.WindowText, _qg.QColor(255,0,0))
            else:
                palette.setColor(palette.WindowText, _qg.QColor(0,255,0))
            self.channel_voltage_lcds[i].setPalette(palette)
            self.channel_current_lcds[i].setPalette(palette)

            if this_hv_channel.auto_reramp_mode == "on":
                self.status_lights[i].setPixmap(_qg.QPixmap('hexesvm/hexe_circle_green.svg'))
            elif this_hv_channel.auto_reramp_mode == "freq_trip":
                self.status_lights[i].setPixmap(_qg.QPixmap('hexesvm/hexe_circle_red.svg'))
            elif this_hv_channel.auto_reramp_mode == "no_dac":
                self.status_lights[i].setPixmap(_qg.QPixmap('hexesvm/hexe_circle_yellow.svg'))
            elif this_hv_channel.auto_reramp_mode == "off":
                self.status_lights[i].setPixmap(_qg.QPixmap('hexesvm/hexe_circle_gray.svg'))
                
            # if Db is connected, run the database insertion of these values
            if self.db_connection:
                self.insert_values_in_database()
                return

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

        form_layout.addRow("address", self.form_address)
        form_layout.addRow("database name", self.form_db)
        form_layout.addRow("table name (HV)", self.form_tablename_hv)
        form_layout.addRow("table name (Interlock)", self.form_tablename_interlock)
        form_layout.addRow("user", self.form_user)
        form_layout.addRow("password", self.form_password)

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
        self.locker.set_interlock_parameter('p1', 0.010)
        
        
    def insert_values_in_database(self):

        MainWindow.log.debug("Called MainWindow.insert_values_in_database")
        cathode_voltage = self.channels["Cathode"].voltage
        gate_voltage = self.channels["Gate"].voltage
        anode_voltage = self.channels["Anode"].voltage
        pmt_top_voltage = self.channels["Top PMT"].voltage
        pmt_bot_voltage = self.channels["Bottom PMT"].voltage        
        
        cathode_current = self.channels["Cathode"].current
        gate_current = self.channels["Gate"].current
        anode_current = self.channels["Anode"].current
        pmt_top_current = self.channels["Top PMT"].current
        pmt_bot_current = self.channels["Bottom PMT"].current 

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
                          "u_pmt_2": pmt_bot_current},])
        
        try:
            self.sql_cont.write_values(insert_array)
            self.db_connection_write = True
            return True
            
        except _sql.exc.ProgrammingError:
        
            self.output_buffer_file.write(str(insert_array)+"\n")
            self.db_connection_write = False
            return False


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
		
