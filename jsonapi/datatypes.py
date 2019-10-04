import datetime as dt

import marshmallow as ma
from sqlalchemy.sql import sqltypes

from jsonapi.exc import DataTypeError

DATETIME_FORMATS = ('%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M',
                    '%Y-%m-%d',
                    '%Y-%m')

DATE_FORMATS = ('%Y-%m-%d', '%Y-%m')
TIME_FORMATS = ('%H:%M:%SZ', '%H:%M')

TRUE_VALUES = ('t', 'true', 'on', '1')
FALSE_VALUES = ('f', 'false', 'off', '0')
NULL_VALUES = ('null', 'none', 'na')


class DataType:
    registry = dict()

    def __init__(self, ma_type, *sa_types, **kwargs):

        self.ma_type = self.get_ma_type(ma_type)

        try:
            iter(sa_types)
        except TypeError:
            self.check_sa_type(sa_types)
            self.sa_types = sa_types,
        else:
            for sa_type in sa_types:
                self.check_sa_type(sa_type)
            self.sa_types = tuple(sa_types)

        parser = kwargs.get('parser', None)
        if parser is not None:
            self.parser = parser
        else:
            self.parser = lambda v: v

        self.filter_clause = None

    def get_ma_type(self, ma_type):
        if not issubclass(ma_type, ma.fields.Field):
            raise ValueError('[{}] ma_type | invalid marshmallow'
                             ' field: {!r}'.format(self.__name__, ma_type))
        return ma_type

    def check_sa_type(self, sa_type):
        if not issubclass(sa_type, sqltypes.TypeEngine):
            raise ValueError('[{}] ma_type | invalid SQLAlchemy'
                             ' sql type: {!r}'.format(self.__name__, sa_type))
        if sa_type in DataType.registry.keys():
            raise ValueError('[{}] sa_type | {!r} sql type is already registered '
                             'to: {!r}'.format(self.__name__,
                                               sa_type,
                                               DataType.registry[sa_type]))
        DataType.registry[sa_type] = self

    def parse(self, val):
        if val.lower() in NULL_VALUES:
            return
        try:
            res = self.parser(val)
        except ValueError:
            raise DataTypeError('invalid value: {}'.format(val), self)
        else:
            return res

    @staticmethod
    def get(expr):
        if expr is not None and hasattr(expr, 'type'):
            return DataType.registry[type(expr.type)]


def parse_bool(val):
    if val.lower() not in TRUE_VALUES and val.lower() not in FALSE_VALUES:
        raise ValueError
    return val.lower() in TRUE_VALUES


def parse_date(val):
    fmt = {len(fmt) + 2: fmt for fmt in DATE_FORMATS}
    if len(val) not in fmt:
        raise ValueError
    return dt.datetime.strptime(val, fmt[len(val)])


def parse_time(val):
    fmt = {len(fmt): fmt for fmt in TIME_FORMATS}
    if len(val) not in fmt:
        raise ValueError
    return dt.datetime.strptime(val, fmt[len(val)])


def parse_datetime(val):
    fmt = {len(fmt) + 2: fmt for fmt in DATETIME_FORMATS}
    if len(val) not in fmt:
        raise ValueError
    return dt.datetime.strptime(val, fmt[len(val)])


Bool = DataType(ma.fields.Boolean, sqltypes.Boolean, parser=parse_bool)
Integer = DataType(ma.fields.Integer,
                   sqltypes.Integer, sqltypes.SmallInteger, sqltypes.BigInteger,
                   parser=int)
Float = DataType(ma.fields.Float, sqltypes.Float, sqltypes.Numeric, parser=int)
String = DataType(ma.fields.String,
                  sqltypes.Text, sqltypes.String, sqltypes.Unicode, sqltypes.Enum)
Date = DataType(ma.fields.Date, sqltypes.Date, parser=parse_date)
Time = DataType(ma.fields.Time, sqltypes.Time, parser=parse_time)
DateTime = DataType(ma.fields.DateTime, sqltypes.DateTime, parser=parse_datetime)
DateTime.FORMAT = DATETIME_FORMATS[0]
