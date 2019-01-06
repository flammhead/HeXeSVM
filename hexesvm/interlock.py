from PyQt5 import QtCore as _qc
import psycopg2 as _psy
import psycopg2.extras as _psyext
import time
import numpy as _np
from datetime import datetime, timedelta


class Interlock(_qc.QThread):

	def __init__(self):
		_qc.QThread.__init__(self)
		self.lock_state = False
		self.is_running = False		
		self.max_time_difference = 120
		self.parameter_value = float('nan')
		self.container = None
		self.is_connected = False
		
		self.connection = None

	def set_sql_container(self, sql_container):

		self.container = sql_container
		
	def set_psycopg_conn(self, host, db_name, user, pwd, tablename):

		con_str = "host='"+host+"' dbname='"+db_name+"' user='"+user+"' password='"+pwd+"'"
		self.table_name = tablename
		self.connection = _psy.connect(con_str)

	def set_interlock_parameter(self, parameter, min_value):
		
		self.lock_param = parameter
		self.time_stamp = "time"
		self.lock_value = min_value
		
	def run(self):
		self.is_running = True
		self.stop_looping = False
		while not self.stop_looping:
			self.check_interlock()
			time.sleep(1)
        	
		
	def check_interlock(self):

		'''
		# THESE LINES BYPASS THE LOCK!
		self.is_conected = True
		self.lock_state = True
		return
		'''
        
		if self.connection is None:
			self.lock_state = False
			return False
		self.is_connected = True

		time_now = datetime.now()
		delta_time = timedelta(seconds=self.max_time_difference)
		time_max_past = time_now - delta_time

		cursor = self.connection.cursor('testName', cursor_factory=_psyext.DictCursor)
		select = 'SELECT '+self.lock_param+' FROM '+self.table_name+' WHERE (time >= %s AND time <= %s)'
		cursor.execute(select, (time_max_past, time_now))
		result = cursor.fetchall()


		data = _np.array(result)
		cursor.close()
		self.is_running = True
		if len(data) == 0:
			print("Interlock received wrong data (too little data) from DB going to Lock!")
			self.lock_state = False
			return False

		try:
			self.parameter_value = (float(data[-1,0]))
		except TypeError:
			print("Interlock received wrong data (wrong type) from DB going to Lock!")
			self.lock_state = False			
			return False

		self.lock_state = self.parameter_value > self.lock_value
		if self.lock_state:
			return True
		else:
			return False
