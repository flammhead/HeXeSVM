# Definition of GUI components containing the HV modules

class gen_module_tab(_qw.QWidget):
    # Class defining how a general HV module interface should look like

    def __init__(self, mother_ui, defaults, hv_module):
        super().__init__(mother_ui)
        self.main_ui = mother_ui
        self.defaults = defaults
        self.module = hv_module


    def _init_module_tabs(self):

        self.module_com_label = _qw.QLabel("Port:")
        self.module_com_line_edits = _qw.QLineEdit(this_tab)
        self.module_com_line_edits.setText(self.module.port)
        
        self.module_is_high_precission_labels        
        self.module_is_high_precission_boxes
        self.module_connect_buttons
        self.module_disconnect_buttons     
        self.module_umax_labels
        self.module_umax_fields     
        self.module_imax_labels
        self.module_imax_fields
        self.module_serial_labels
        self.module_serial_fields      
        self.module_firmware_labels 
        self.module_firmware_fields
        self.module_svgs
        self.module_hsep             
        self.module_vsep
        self.module_grid_layouts  
    
    
    
    
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
        self.module_svgs = []
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
            this_high_precision_box.setToolTip("Check if this channel provides high-precision read out!")
            self.module_is_high_precission_boxes.append(this_high_precision_box)
            
            this_connect_button = _qw.QPushButton("&Connect")
            self.module_connect_buttons.append(this_connect_button)
            this_connect_button.clicked.connect(partial(self.connect_hv_module, key, i))
            
            this_disconnect_button = _qw.QPushButton("&Disconnect")
            this_disconnect_button.setEnabled(False)               
            self.module_disconnect_buttons.append(this_disconnect_button)
            this_disconnect_button.clicked.connect(partial(self.disconnect_hv_module, key, i))      
            
            this_u_max_label = _qw.QLabel("U(V):")
            this_u_max_label.setToolTip("Maximum output voltage of the board")
            self.module_umax_labels.append(this_u_max_label)
            this_u_max_field = _qw.QLineEdit(this_tab)
            this_u_max_field.setToolTip("Maximum output voltage of the board")
            this_u_max_field.setDisabled(True)
            self.module_umax_fields.append(this_u_max_field)
            
            this_i_max_label = _qw.QLabel("I(mA):")
            this_i_max_label.setToolTip("Maximum output current of the board")
            self.module_imax_labels.append(this_i_max_label)
            this_i_max_field = _qw.QLineEdit(this_tab)
            this_i_max_field.setToolTip("Maximum output current of the board")
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

            this_mod_type = self.defaults['modules'][i]['type']
            if this_mod_type == "NHQ":
                this_module_svg  = _qs.QSvgWidget('hexesvm/icons/iseg_nhq_front_1_discon.svg', this_tab)
            elif this_mod_type == "NHR":
                this_module_svg  = _qs.QSvgWidget('hexesvm/icons/iseg_nhr_front_3_discon.svg', this_tab)

            self.module_svgs.append(this_module_svg) 
            svg_min_size = _qc.QSize(82,538)
            svg_max_size = _qc.QSize(82,538)
            this_module_svg.setMinimumSize(svg_min_size)
            this_module_svg.setMaximumSize(svg_max_size)
            
            horizontal_separator = _qw.QLabel("")
            self.module_hsep.append(horizontal_separator)
            horizontal_separator.setFrameStyle(_qw.QFrame.HLine)
            horizontal_separator.setLineWidth(2)
        
            grid = _qw.QGridLayout()
            grid.setSpacing(10)
            # Row 1 widgetd
            grid.addWidget(this_com_port_label, 1,2)
            grid.addWidget(this_com_port, 1,3,1,1)
            grid.addWidget(this_connect_button, 1,4, 1,1, _qc.Qt.AlignHCenter)
            grid.addWidget(this_disconnect_button, 1,5, 1,1, _qc.Qt.AlignHCenter)            
            # Row 2 and 3 widgets
            grid.addWidget(this_u_max_label, 2,2)
            grid.addWidget(this_u_max_field, 2,3)
            grid.addWidget(this_i_max_label, 2,4)
            grid.addWidget(this_i_max_field, 2,5)
            grid.addWidget(this_serial_number_label, 3,2)
            grid.addWidget(this_serial_number_field, 3,3)  
            grid.addWidget(this_firmware_label, 3,4)
            grid.addWidget(this_firmware_field, 3,5)
            grid.addWidget(this_high_precision_label, 1, 6, 2,1)
            grid.addWidget(this_high_precision_box, 3,6)

            grid.addWidget(this_module_svg, 1,7,12,2)
            grid.addWidget(horizontal_separator, 4,1,1,6)
           

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
        
    def update_module_tabs(self):
        #MainWindow.log.debug("Called MainWindow.update_module_tabs")
        for i, key in zip(range(len(self.modules)), self.modules.keys()):    
            this_tab = self.mod_tabs[key]
            this_module = self.modules[key]
            
            self.module_umax_fields[i].setText(this_module.u_max)
            self.module_imax_fields[i].setText(this_module.i_max)
            self.module_serial_fields[i].setText(this_module.model_no)
            self.module_firmware_fields[i].setText(this_module.firmware_vers)

            # update the "virtual" module
            # DO SOME MAGIC HERE

            # Trigger update of the channel sections
            for idx in range(len(self.channels[key].keys())):
                 self.update_channel_section(key, list(self.channels[key].keys())[idx])

        return
        
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
            
        
    def connect_hv_module(self, key, index):
        MainWindow.log.debug("connecting "+key)  
        self.statusBar().showMessage("connecting "+key)
        com_port = self.module_com_line_edits[index].text().strip()
        self.modules[key].set_comport(com_port)
        is_high_precission = self.module_is_high_precission_boxes[index].checkState()
        self.modules[key].is_high_precission = is_high_precission
        
        try:
            self.modules[key].establish_connection()
            
        except FileNotFoundError:
            MainWindow.log.warning("Could not connect to HV Module: "
                   			"Wrong COM Port")
            self.statusBar().showMessage("Wrong COM Port")
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
        self.statusBar().showMessage("disconnecting "+key)
        self.stop_reader_thread(self.modules[key])
        
        self.modules[key].close_connection()
        self.module_com_line_edits[index].setDisabled(False)      
        self.module_is_high_precission_boxes[index].setEnabled(True)        
        self.module_disconnect_buttons[index].setEnabled(False)        
        self.module_connect_buttons[index].setEnabled(True)
        return
        
    def start_reader_thread(self, module):
        if module.is_connected:
            if not module.reader_thread:
                module_thread = _thr.MonitorIsegModule(module)
                module.set_reader_thread(module_thread)
                module_thread.start()
                MainWindow.log.debug("thread "+module.name+" started")
                self.statusBar().showMessage("thread "+module.name+" started") 
        return

    def stop_reader_thread(self, module):
        if not module.is_connected:
            return False
        module.stop_running_thread()      

        while module.board_occupied:
            MainWindow.log.debug("Waiting for thread "+module.name+" to stop")
            self.statusBar().showMessage("Waiting for thread "+module.name+" to stop")
            time.sleep(0.2)
        MainWindow.log.debug("thread "+module.name+" stopped")
        self.statusBar().showMessage("thread "+module.name+" stopped")
        return True

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

