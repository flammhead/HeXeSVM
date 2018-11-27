"""Defines functions/classes for SQL i/o"""
from collections import OrderedDict as _OrderedDict
import logging as _lg
import numpy as _np
import sqlalchemy as _sql


class SqlWriter():
    """Defines a container class for SQL data"""

    def __init__(self, dialect, address, dbname, tablename, username, password):
        self.params = _OrderedDict()
        self.prev_query_time = 0

        # set up database access
        sqlalch_url = "{:s}://{:s}:{:s}@{:s}/{:s}".format(dialect, username,
                                                          password, address,
                                                          dbname)
        self.engine = _sql.create_engine(sqlalch_url)

        # infer table structure
        self.table_meta = _sql.MetaData()
        self.table = _sql.Table(tablename, self.table_meta, autoload=True,
                                autoload_with=self.engine)
        self.cols = [col.name for col in self.table.columns]

        # start connection
        self.conn = self.engine.connect()

            
    def write_values(self, ordered_value):
        values = ordered_value
        insert = _sql.sql.insert(self.table, values)
        result = self.conn.execute(insert)
            
