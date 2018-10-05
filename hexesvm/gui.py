"""Contains the HeXeSVM User interface"""

import logging as _lg
from PyQt5 import QtCore as _qc
from PyQt5 import QtGui as _qg
from PyQt5 import QtWidgets as _qw


# create module logger
_gui_log = _lg.getLogger("hexesvm.gui")
_gui_log.setLevel(_lg.DEBUG)
_lg.debug("Loading hexesvm.gui")


class MainWindow(_qw.QMainWindow):

	log = _lg.getLogger("hexesvm.gui.MainWindow")

	def __init__(self):

		super().__init__()
		MainWindow.log.debug("Created MainWindow")
		self.startUI()

	def startUI(self):
		
		self._init_geom()
		self._init_menu()
		self._init_status_bar()
		self._init_subwindows()
		


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

	def _init_subwindows(self):
		"""Create the tabs"""
		MainWindow.log.debug("Called MainWindow._init_subwindows")
		self.main_widget = _qw.QTabWidget(self)
		self.setCentralWidget(self.main_widget)
		self.overviewTab = _qw.QWidget(self.main_widget)
		self.settingsTab = _qw.QWidget(self.main_widget)
		self.main_widget.addTab(self.overviewTab, "Overview")
		self.main_widget.addTab(self.settingsTab, "Settings")
	
	def closeEvent(self, event):
		if not self.file_quit():
			event.ignore()

	def file_quit(self):
		"""Closes the application"""
		MainWindow.log.debug("Called MainWindow.file_quit")


		reply = _qw.QMessageBox.question(self, 'Confirm',
			'Are you sure to quit?', _qw.QMessageBox.Yes |
			_qw.QMessageBox.No | _qw.QMessageBox.Cancel, 				_qw.QMessageBox.Cancel)
		if reply == _qw.QMessageBox.Yes:
			self.close()
			return(True)
		else:
			return(False)
		
