import datetime as dt
import json

import marshmallow as ma
from sqlalchemy.sql import sqltypes

from jsonapi.db.filter import FilterClause, Operator
from jsonapi.exc import DataTypeError


class DataType:
    FORMATS_DATETIME = ('%Y-%m-%dT%H:%M:%SZ',
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%dT%H:%M',
                        '%Y-%m-%d',
                        '%Y-%m',
                        '%H:%M:%S',
                        '%H:%M')

    VALUES_TRUE = ('t', 'true', 'on', '1')
    VALUES_FALSE = ('f', 'false', 'off', '0')
    VALUES_NULL = ('null', 'none', 'na')

    registry = dict()

    def __init__(self, ma_type, *sa_types, **kwargs):
        self.ma_type = self.get_ma_type(ma_type)
        self.sa_types = tuple(self.get_sa_type(sa_type) for sa_type in sa_types)
        self.parser = kwargs.get('parser', str)
        operators, operators_multi = kwargs.get(
            'filter', ((Operator.NONE, Operator.EQ, Operator.NE),
                       (Operator.NONE, Operator.EQ, Operator.NE)))
        self.filter_clause = FilterClause(self, *operators, multiple=operators_multi)

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

    @classmethod
    def get_datetime_format(cls, val):
        for fmt in cls.FORMATS_DATETIME:
            length = len(val) - 2 if '-' in val else len(val)
            if len(fmt) == length:
                if len(fmt) > 8:
                    return fmt
                if '-' in fmt and '-' in val:
                    return fmt
                if ':' in fmt and ':' in val:
                    return fmt
        return cls.FORMATS_DATETIME[0]

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
    if val.lower() not in DataType.VALUES_TRUE and val.lower() not in DataType.VALUES_FALSE:
        raise ValueError
    return val.lower() in DataType.VALUES_TRUE


def parse_datetime(val):
    return dt.datetime.strptime(val, DataType.get_datetime_format(val))


Bool = DataType(
    ma.fields.Bool,
    sqltypes.Boolean,
    parser=parse_bool,
    filter=((Operator.NONE, Operator.EQ), None))

Integer = DataType(
    ma.fields.Integer,
    sqltypes.Integer,
    parser=int,
    filter=((Operator.NONE, Operator.EQ, Operator.NE,
             Operator.GT, Operator.GE, Operator.LT, Operator.LE),
            (Operator.NONE, Operator.EQ, Operator.NE)))

Float = DataType(
    ma.fields.Float,
    sqltypes.Numeric,
    parser=float,
    filter=((Operator.GT, Operator.GE, Operator.LT, Operator.LE),
            (Operator.NONE, Operator.EQ, Operator.NE)))

String = DataType(
    ma.fields.String,
    sqltypes.Text, sqltypes.String, sqltypes.Enum,
    filter=((Operator.NONE, Operator.EQ, Operator.NE),
            (Operator.NONE, Operator.EQ, Operator.NE)))

Date = DataType(
    ma.fields.Date,
    sqltypes.Date,
    parser=parse_datetime,
    filter=((Operator.GT, Operator.LT),
            (Operator.NONE, Operator.EQ, Operator.NE)))

Time = DataType(
    ma.fields.Time,
    sqltypes.Time,
    parser=parse_datetime,
    filter=((Operator.GT, Operator.LT),
            (Operator.NONE, Operator.EQ, Operator.NE)))

DateTime = DataType(
    ma.fields.DateTime,
    sqltypes.DateTime,
    parser=parse_datetime,
    filter=((Operator.GT, Operator.LT),
            (Operator.NONE, Operator.EQ, Operator.NE)))


class JSONField(ma.fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return json.loads(value) if value is not None else None

    def _deserialize(self, value, attr, data, **kwargs):
        return json.dumps(value)


JSON = DataType(JSONField, sqltypes.JSON)

DateTime.FORMAT = DataType.FORMATS_DATETIME[0]
Date.FORMAT = DataType.FORMATS_DATETIME[3]
