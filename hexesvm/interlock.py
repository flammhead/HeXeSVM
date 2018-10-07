import sqlalchemy as _sql
import time
import numpy as _np
from datetime import datetime, timedelta

class Interlock():

	def __init__(self):
		self.lock_state = False
		self.max_time_difference = 10
		self.parameter_value = float('nan')
		self.container = None

	def set_sql_container(self, sql_container):

		self.container = sql_container

	def set_interlock_parameter(self, parameter, min_value):
		
		self.lock_param = parameter
		self.time_stamp = "time"
		self.lock_value = min_value		
		
	def check_interlock(self):

		if self.container is None:
			self.lock_stat = False
			return False

		time_now = datetime.now()
		delta_time = timedelta(seconds=self.max_time_difference)
		time_max_past = time_now - delta_time

		sel = _sql.sql.select((self.container.table.columns[self.lock_param], self.container.table.columns[self.time_stamp])).where((self.container.table.columns[self.time_stamp] >=
                                            time_max_past) &
                                            (self.container.table.columns[self.time_stamp] <=
                                            time_now))		
		result = self.container.conn.execute(sel)
		data = _np.array(result.fetchall())
		if len(data) == 0:
			self.lock_state = False
			return False

		try:
			self.parameter_value = float(data[-1,0])
		except TypeError:
			return False

		self.lock_state = self.parameter_value > self.lock_value
		if self.lock_state:
			return True
		else:
			return False
