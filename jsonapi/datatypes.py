import datetime as dt
import json

import marshmallow as ma
from sqlalchemy.sql import sqltypes

from jsonapi.db.filter import FilterClause, Operator
from jsonapi.exc import DataTypeError

accept_date = ('%Y-%m-%d', '%Y-%m')
accept_time = ('%H:%M:%S', '%H:%M', '%I:%M%p', '%I:%M %p')
accept_datetime = ('%Y-%m-%dT%H:%M:%SZ',
                   '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %I:%M:%S%p',
                   '%Y-%m-%d %I:%M:%S %p',
                   '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %I:%M', '%Y-%m-%d %I:%M%p',
                   '%Y-%m-%d %I:%M %p')


class DataType:
    FORMAT_DATETIME = '%Y-%m-%dT%H:%M:%SZ'
    FORMAT_DATE = '%Y-%m-%d'
    FORMAT_TIME = '%H:%M:%S'

    VALUES_TRUE = ('t', 'true', 'on', '1', 'yes')
    VALUES_FALSE = ('f', 'false', 'off', '0', 'no')
    VALUES_NULL = ('null', 'none', 'na')

    registry = dict()

    def __init__(self, ma_type, *sa_types, **kwargs):
        self.ma_type = self.get_ma_type(ma_type)
        self.sa_types = tuple(self.get_sa_type(sa_type) for sa_type in sa_types)
        self.parser = kwargs.get('parser', str)
        self.accept = kwargs.get('accept', tuple())
        self.filter_clause = FilterClause(self, *kwargs.get('filter_ops', (Operator.NONE,)),
                                          multiple=kwargs.get('filter_ops_multi', None))

    @property
    def name(self):
        return self.ma_type.__name__

    def get_ma_type(self, ma_type):
        if not issubclass(ma_type, ma.fields.Field):
            raise ValueError('[{}] ma_type | invalid marshmallow'
                             ' field: {!r}'.format(self.name, ma_type))
        return ma_type

    def get_sa_type(self, sa_type):
        if not issubclass(sa_type, sqltypes.TypeEngine):
            raise ValueError('[{}] sa_type | invalid SQLAlchemy'
                             ' sql type: {!r}'.format(self.name, sa_type))
        if sa_type in DataType.registry.keys():
            raise ValueError('[{}] sa_type | {!r} sql type is already registered '
                             'to: {!r}'.format(self.name, sa_type, DataType.registry[sa_type]))
        DataType.registry[sa_type] = self
        return sa_type

    def parse(self, val):
        if val.lower() in DataType.VALUES_NULL:
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
            for sa_type, data_type in DataType.registry.items():
                if isinstance(expr.type, sa_type):
                    return data_type

    def __repr__(self):
        return '<{}>'.format(self.name)


def parse_bool(val):
    if not isinstance(val, str):
        raise ValueError
    if val.lower() not in DataType.VALUES_TRUE and val.lower() not in DataType.VALUES_FALSE:
        raise ValueError
    return val.lower() in DataType.VALUES_TRUE


def parse_date(val):
    if not isinstance(val, str):
        raise ValueError
    for fmt in accept_date:
        try:
            return dt.datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    raise ValueError


def parse_time(val):
    if not isinstance(val, str):
        raise ValueError
    for fmt in accept_time:
        try:
            return dt.datetime.strptime(val, fmt).time()
        except ValueError:
            pass
    raise ValueError


def parse_datetime(val):
    if not isinstance(val, str):
        raise ValueError
    for fmt in (*accept_datetime, *accept_date):
        try:
            return dt.datetime.strptime(val, fmt)
        except ValueError:
            pass
    raise ValueError


Bool = DataType(
    ma.fields.Bool,
    sqltypes.Boolean,
    parser=parse_bool,
    filter_ops=(Operator.NONE, Operator.EQ, Operator.NE),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))

Integer = DataType(
    ma.fields.Integer,
    sqltypes.Integer,
    parser=int,
    filter_ops=(Operator.NONE, Operator.EQ, Operator.NE,
                Operator.GT, Operator.GE, Operator.LT, Operator.LE),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))

Float = DataType(
    ma.fields.Float,
    sqltypes.Numeric,
    parser=float,
    filter_ops=(Operator.GT, Operator.GE, Operator.LT, Operator.LE),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))

String = DataType(
    ma.fields.String,
    sqltypes.Text, sqltypes.String, sqltypes.Enum,
    filter_ops=(Operator.NONE, Operator.EQ, Operator.NE),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))

Date = DataType(
    ma.fields.Date,
    sqltypes.Date,
    parser=parse_date,
    filter_ops=(Operator.GT, Operator.LT),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))

Time = DataType(
    ma.fields.Time,
    sqltypes.Time,
    parser=parse_time,
    filter_ops=(Operator.GT, Operator.LT),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))

DateTime = DataType(
    ma.fields.DateTime,
    sqltypes.DateTime,
    parser=parse_datetime,
    filter_ops=(Operator.GT, Operator.LT),
    filter_ops_multi=(Operator.NONE, Operator.EQ, Operator.NE))


class JSONField(ma.fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return json.loads(value) if value is not None else None

    def _deserialize(self, value, attr, data, **kwargs):
        return json.dumps(value)


JSON = DataType(JSONField, sqltypes.JSON)
