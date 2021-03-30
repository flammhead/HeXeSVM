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
        self.index_list = [] # Helper dict for sorting later on
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
               self.index_list.append([this_channel['img_pos'], this_module['name'], this_channel['name']])
           self.channels.update({this_module['name']: this_mod_chan})

        # Also construct one dict which holds the module/channel combination in the order
        # they should appear on the overview page
        self.channel_order_dict = []
        for i in range(len(self.index_list)):
           pos = -1
           for j in range(len(self.index_list)):
               if self.index_list[j][0] == i:
                   pos = j
           self.channel_order_dict.append((self.index_list[pos][1], self.index_list[pos][2]))

        
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

        # Disable the auto-reramp boxes
        for this_module_tab in self.mod_tabs.values():
            for this_channel_tab in this_module_tab.channel_tabs:
                this_channel_tab.auto_reramp_box.setCheckState(False)
                this_channel_tab.auto_reramp_box.setEnabled(False)

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
            self.mod_tabs[key].start_reader_thread()               

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
        self.file_menu.addAction("&Quit", self.close,
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
            this_y_position = grid_layout_y_positions[i] 
            grid.addWidget(self.channel_labels[i], this_y_position, 1)
            grid.addWidget(self.channel_voltage_lcds[i], this_y_position, 2)
            grid.addWidget(self.voltage_units[i], this_y_position, 3)
            grid.addWidget(self.channel_current_lcds[i], this_y_position, 4)
            grid.addWidget(self.current_units[i], this_y_position, 5)
            grid.addWidget(self.status_lights[i], this_y_position, 6)

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

        for this_module in mod_tabs.values():
            for this_channel in this_module.channel_tabs.values():
                for this_widget in this_channel.disable_in_auto_mode:
                    this_widget.setEnabled(True)

        self.rampTableRunButton.setEnabled(False)        
        self.rampTableStopButton.setEnabled(True)
        
        #start the auto ramp thread
        self.auto_ramp_thread = _thr.ScheduleRampIsegModule(self)
        # connect thread's signals to the respective apply and ramp functions

        #TODO
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
        for this_module in mod_tabs.values():
            for this_channel in this_module.channel_tabs.values():
                for this_widget in this_channel.disable_in_auto_mode:
                    this_widget.setEnabled(True)
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
        self.form_email_info.setEnabled(False)
        self.form_email_alarm.setEnabled(False)
        self.form_email_sms.setEnabled(False)
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

        this_channel_tab = self.mod_tabs[mod_key].channel_tabs[channel_key]
        if self.email_sender.recipients_info == "" or self.email_sender.recipients_alarm == "":
            self.err_msg_mail = _qw.QMessageBox.warning(self, "Mail",
                                   "Set info & and alarm email recipients first!")
            return False
        if alarm_mode == "single":
            sms_flag = this_channel_tab.single_sms_box.checkState()
            priority = this_channel_tab.single_button_group.checkedId()
        elif alarm_mode == "frequent":
            sms_flag = this_channel_tab.frequent_sms_box.checkState()
            priority = this_channel_tab.frequent_button_group.checkedId()

        hv_channel = this_channel_tab.channel
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
	
    def closeEvent(self, event):
        if self.file_quit_diag():
            event.accept()
        else:
           event.ignore()
    
    def file_quit_diag(self):
        """Closes the application"""
        MainWindow.log.debug("Called MainWindow.file_quit")
        self.statusBar().showMessage("Quitting application")

        reply = _qw.QMessageBox.question(self, 'Confirm',
	        'Are you sure to quit?', _qw.QMessageBox.Yes |
	        _qw.QMessageBox.No | _qw.QMessageBox.Cancel, 				
	        _qw.QMessageBox.Cancel)
        if reply == _qw.QMessageBox.Yes:
            # Disconnect the modules
            for this_module in self.mod_tabs.values():
                if this_module.module.is_connected:
                    this_module.disconnect_hv_module()
            return(True)
        else:
            return(False)

