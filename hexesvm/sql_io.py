"""Defines functions/classes for SQL i/o"""
from collections import OrderedDict as _OrderedDict
import logging as _lg
import numpy as _np
import sqlalchemy as _sql


# create module logger
_sql_log = _lg.getLogger("magic.sql_io")
_sql_log.setLevel(_lg.DEBUG)
_lg.debug("Loading magic.sql_io")

class SqlContainer():
    """Defines a container class for SQL data"""
    log = _lg.getLogger("magic.sql_gui.SqlContainer")

    def __init__(self, dialect, address, dbname, tablename, username, password):
        SqlContainer.log.debug("Created SqlContainer instance")
        self.params = _OrderedDict()
        self.prev_query_time = 0

        # set up database access
        sqlalch_url = "{:s}://{:s}:{:s}@{:s}/{:s}".format(dialect, username,
                                                          password, address,
                                                          dbname)
        SqlContainer.log.info("Connecting to {:s} at {:s} as {:s}".format(dbname, address,
                                                             username))
        self.engine = _sql.create_engine(sqlalch_url, server_side_cursors=True)
        SqlContainer.log.info("Connection established")

        # infer table structure
        self.table_meta = _sql.MetaData()
        self.table = _sql.Table(tablename, self.table_meta, autoload=True,
                                autoload_with=self.engine)
        self.cols = [col.name for col in self.table.columns]

        # start connection
        self.conn = self.engine.connect()

    def add_param(self, param_name):
        SqlContainer.log.debug("Called SqlContainer.add_param")
        self.params[param_name] = _np.zeros(1)

    def remove_param(self, param_name):
        SqlContainer.log.debug("Called SqlContainer.remove_param")
        del self.params[param_name]

    def update(self, time_param_name, time_start, time_end):
        SqlContainer.log.debug("Called SqlContainer.update")
        params = [self.table.columns[time_param_name]]
        params.extend([self.table.columns[param] for param in
                       self.params.keys()])
        sel = _sql.sql.select(params).where((self.table.columns[time_param_name] >=
                                            time_start) &
                                            (self.table.columns[time_param_name] <=
                                            time_end))
        result = self.conn.execute(sel)
        data = _np.array(result.fetchall())

        SqlContainer.log.debug("Fetched {:d} rows".format(len(data)))

        if not len(data) > 0:
            data = _np.zeros((1, len(params)))

        self.times = data[:, 0].astype(_np.datetime64(1, "ms"))

        # convert to UNIX timestamp
        self.times = ((self.times - _np.datetime64('1970-01-01T00:00:00Z')) /
                      _np.timedelta64(1, "s"))

        for n, param_name in enumerate(self.params.keys()):
            self.params[param_name] = data[:, n+1].astype(_np.float32)
