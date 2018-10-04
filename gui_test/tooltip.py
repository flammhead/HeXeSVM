import sys
from PyQt5.QtWidgets import (QWidget, QToolTip, QPushButton, QApplication, QMessageBox, QMainWindow, QAction, 
				qApp, QLabel, QGridLayout, QLineEdit, QLCDNumber, QFrame)
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter
import PyQt5.QtCore
from PyQt5.QtSvg import QSvgWidget

class Example(QMainWindow):

	def __init__(self):

		super().__init__()
		self.startUI()

	def startUI(self):

		
		self.statusBar().showMessage('Program started')
		self.frame = QFrame()
		self.setCentralWidget(self.frame)
		QToolTip.setFont(QFont('SansSerif', 10))

		exitAct = QAction('&Exit', self)
		exitAct.setShortcut('Ctrl+Q')
		exitAct.setToolTip("Closes application")
		exitAct.triggered.connect(qApp.quit)
		menuBar = self.menuBar()
		fileMenu = menuBar.addMenu('&File')
		fileMenu.addAction(exitAct)
		
		central_widget = QWidget()
		self.stat_size=10

		self.status_lights = ((QSvgWidget('hexe_circle_gray.svg'), QSvgWidget('hexe_circle_gray.svg'),
					QSvgWidget('hexe_circle_gray.svg'), QSvgWidget('hexe_circle_gray.svg'),
					QSvgWidget('hexe_circle_gray.svg')))
		for i in self.status_lights:
			i.resize(self.stat_size, self.stat_size)
		
		self.hexe_drawing = QSvgWidget('hexe_sketch_hv.svg')

		self.n_lcd_digits = 5

		self.channel_names = ((QLabel('Top PMT'),QLabel('Anode'),QLabel('Gate'),QLabel('Cathode'),QLabel('Bottom PMT')))

		self.voltages = ((QLCDNumber(),QLCDNumber(),QLCDNumber(),QLCDNumber(),QLCDNumber()))
		
		for i in self.voltages:
			i.setNumDigits(self.n_lcd_digits)
			i.display('Error')
			i.setSegmentStyle(QLCDNumber.Flat)
			palette = i.palette()
			palette.setColor(palette.WindowText, QColor(0,255,0))
			palette.setColor(palette.Background, QColor(10,10,10))
			i.setPalette(palette)
			i.setAutoFillBackground(True)


		self.voltage_units = ((QLabel('V'),QLabel('V'),QLabel('V'),QLabel('V'),QLabel('V')))

		self.currents = ((QLCDNumber(),QLCDNumber(),QLCDNumber(),QLCDNumber(),QLCDNumber()))
		for j in self.currents:
			j.setNumDigits(self.n_lcd_digits)
			j.display('Error')
			j.setSegmentStyle(QLCDNumber.Flat)
			palette = j.palette()
			palette.setColor(palette.WindowText, QColor(0,255,0))
			palette.setColor(palette.Background, QColor(10,10,10))
			j.setPalette(palette)
			j.setAutoFillBackground(True)

		self.current_units = ((QLabel('µA'),QLabel('µA'),QLabel('µA'),QLabel('µA'),QLabel('µA')))

		status_label_text = QLabel('re-ramp')

		grid = QGridLayout()
		grid.setSpacing(10)

		positions = ((1,2,3,5,6))
		'''
		for drawing, y_pos  in zip(self.svg_drawings, positions):
			grid.addWidget(drawing, y_pos, 0)
		'''
		grid.addWidget(self.hexe_drawing, 1,0,6,1)
		for label, y_pos in zip(self.channel_names, positions):
			grid.addWidget(label, y_pos, 1)
		for voltage, y_pos in zip(self.voltages, positions):
			grid.addWidget(voltage, y_pos, 2)

		for v_units, y_pos in zip(self.voltage_units, positions):
                        grid.addWidget(v_units, y_pos, 3)

		for current, y_pos in zip(self.currents, positions):
			grid.addWidget(current, y_pos, 4)

		for a_units, y_pos in zip(self.current_units, positions):
			grid.addWidget(a_units, y_pos, 5)

		grid.addWidget(status_label_text, 0,6)
		for stat, y_pos in zip(self.status_lights, positions):
			grid.addWidget(stat, y_pos, 6)

		central_widget.setLayout(grid)
		self.setCentralWidget(central_widget)

		self.setGeometry(250,150,400,200)
		self.setWindowTitle('test')
		self.show()


	def closeEvent(self, event):

		reply = QMessageBox.question(self, 'Confirm',
			'Are you sure to quit?', QMessageBox.Yes |
			QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
		if reply == QMessageBox.Yes:
			event.accept()
		else:
			event.ignore()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	ex = Example()
	sys.exit(app.exec_())
