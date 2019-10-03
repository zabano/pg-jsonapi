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
    ma_type = None
    """
    Marshmallow field to use for serialization.
    """

    sa_types = tuple()
    """
    SQLAlchemy data types to map to this data type class
    """

    registry = dict()
    """
    A registry of data types, keyed by sql type
    """

    filter_clause = None
    """
    A `jsonapi.db.filter.FilterClause <FilterClause>` instance
    """

    def __init_subclass__(cls, **kwargs):

        cls.check_ma_type()

        try:
            iter(cls.sa_types)
        except TypeError:
            cls.check_sa_type(cls.sa_types)
            cls.sa_types = cls.sa_types,
        else:
            for sa_type in cls.sa_types:
                cls.check_sa_type(sa_type)
            cls.sa_types = tuple(cls.sa_types)

    @classmethod
    def check_ma_type(cls):
        if not issubclass(cls.ma_type, ma.fields.Field):
            raise ValueError('[{}] ma_type | invalid marshmallow'
                             ' field: {!r}'.format(cls.__name__, cls.ma_type))

    @classmethod
    def check_sa_type(cls, sa_type):
        if not issubclass(sa_type, sqltypes.TypeEngine):
            raise ValueError('[{}] ma_type | invalid SQLAlchemy'
                             ' sql type: {!r}'.format(cls.__name__, sa_type))
        if sa_type in DataType.registry.keys():
            raise ValueError('[{}] sa_type | {!r} sql type is already registered '
                             'to: {!r}'.format(cls.__name__,
                                               sa_type,
                                               DataType.registry[sa_type]))
        DataType.registry[sa_type] = cls

    @classmethod
    def parse(cls, val):
        """
        Parse string value into a Python native type.

        :param str val: value to parse
        :return: parsed value
        """
        return val


class Bool(DataType):
    ma_type = ma.fields.Bool
    sa_types = sqltypes.Boolean

    @classmethod
    def parse(cls, val):
        if val.lower() in NULL_VALUES:
            return
        if val.lower() not in TRUE_VALUES and val.lower() not in FALSE_VALUES:
            raise DataTypeError('invalid value: {}'.format(val), cls)
        return val.lower() in TRUE_VALUES


class Integer(DataType):
    ma_type = ma.fields.Integer
    sa_types = sqltypes.Integer, sqltypes.SmallInteger, sqltypes.BigInteger

    @classmethod
    def parse(cls, val):
        if val.lower() in NULL_VALUES:
            return
        try:
            return int(val)
        except ValueError:
            raise DataTypeError('invalid value: {}'.format(val), cls)


class Float(DataType):
    ma_type = ma.fields.Float
    sa_types = sqltypes.Float, sqltypes.Numeric

    @classmethod
    def parse(cls, val):
        if val.lower() in NULL_VALUES:
            return
        try:
            return float(val)
        except ValueError:
            raise DataTypeError('invalid value: {}'.format(val), cls)


class Date(DataType):
    ma_type = ma.fields.Date
    sa_types = sqltypes.Date

    @classmethod
    def parse(cls, val):
        if val.lower() in NULL_VALUES:
            return
        fmt = {len(fmt) + 2: fmt for fmt in DATE_FORMATS}
        if len(val) not in fmt:
            raise DataTypeError('invalid value: {}'.format(val), cls)
        return dt.datetime.strptime(val, fmt[len(val)])


class Time(DataType):
    ma_type = ma.fields.Time
    sa_types = sqltypes.Time

    @classmethod
    def parse(cls, val):
        if val.lower() in NULL_VALUES:
            return
        fmt = {len(fmt): fmt for fmt in TIME_FORMATS}
        if len(val) not in fmt:
            raise DataTypeError('invalid value: {}'.format(val), cls)
        return dt.datetime.strptime(val, fmt[len(val)])


class DateTime(DataType):
    FORMAT = DATETIME_FORMATS[0]

    ma_type = ma.fields.DateTime
    sa_types = sqltypes.DateTime

    @classmethod
    def parse(cls, val):
        if val.lower() in NULL_VALUES:
            return
        fmt = {len(fmt) + 2: fmt for fmt in DATETIME_FORMATS}
        if len(val) not in fmt:
            raise DataTypeError('invalid value: {}'.format(val), cls)
        return dt.datetime.strptime(val, fmt[len(val)])


class String(DataType):
    ma_type = ma.fields.String
    sa_types = sqltypes.Text, sqltypes.String, sqltypes.Unicode, sqltypes.Enum


def get_data_type(expr):
    if expr is not None and hasattr(expr, 'type'):
        return DataType.registry[type(expr.type)]
