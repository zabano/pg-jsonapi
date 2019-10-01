import enum
import re

from sqlalchemy.sql import operators, or_

from jsonapi.datatypes import DataType, Bool, Integer, Float, String, Date, Time, DateTime
from .table import is_clause, is_from_item
from .util import *

MODIFIERS = {'=': operators.eq, '<>': operators.ne, '!=': operators.ne,
             '>=': operators.ge, '<=': operators.le, '>': operators.gt, '<': operators.lt}


class Operator(enum.Enum):
    NONE = ''
    EQ = 'eq'
    NE = 'ne'
    GT = 'gt'
    GE = 'ge'
    LT = 'lt'
    LE = 'le'


OPERATOR_NONE = Operator.NONE
OPERATOR_EQ = Operator.EQ
OPERATOR_NE = Operator.NE
OPERATOR_GT = Operator.GT
OPERATOR_GE = Operator.GE
OPERATOR_LT = Operator.LT
OPERATOR_LE = Operator.LE


class FilterClause:
    data_type = String
    operators = tuple()
    multiple = tuple()

    registry = dict()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        FilterClause.registry[cls.data_type.value] = cls()

    def __init__(self):

        if not isinstance(self.data_type, DataType):
            raise ValueError('[FilterExpression] invalid datatype: {!r}'.format(self.data_type))

        for op in self.operators:
            if not isinstance(op, Operator):
                raise ValueError('[FilterExpression] invalid operator: {!r}'.format(op))

        for op in self.multiple:
            if not isinstance(op, Operator):
                raise ValueError('[FilterExpression] invalid operator: {!r}'.format(op))

    def is_op(self, op, multiple=False):
        return op in (o.value for o in (self.multiple if multiple else self.operators))

    def parse_values(self, val):
        if any(symbol in val for symbol in MODIFIERS):
            values = list()
            for v in val.split(','):
                match = re.match('({})?(\w+)'.format('|'.join(MODIFIERS)), v)
                if match:
                    mod = '=' if not match[1] else match[1]
                    values.append((mod, self.parse(match[2])))
            return values
        else:
            return [('=', self.parse(v)) for v in val.split(',')]

    @staticmethod
    def parse(val):
        return val

    def get(self, expr, op, val):

        #
        # multiple values
        #
        if ',' in val:
            if not self.is_op(op, multiple=True):
                raise Error('invalid operator: {}'.format(op))

            values = self.parse_values(val)
            if all(mod == '=' for mod, _ in values):
                if op in ('', 'eq'):
                    return expr.in_(val for _, val in values)
                elif op == 'ne':
                    return expr.notin_(val for _, val in values)
                else:
                    raise Error('invalid operator: {}')
            else:
                expressions = list()
                for mod, val in values:
                    if val in (True, False, None):
                        if mod == '=':
                            expressions.append(expr.is_(val))
                        elif mod in ('!=', '<>'):
                            expressions.append(expr.isnot(val))
                        else:
                            raise Error('invalid modifier: {}'.format(mod))
                    else:
                        expressions.append(MODIFIERS[mod](expr, val))
                return or_(*expressions)

        #
        # single values
        #
        else:
            if not self.is_op(op):
                raise Error('invalid operator: {}'.format(op))
            if op == '':
                op = 'eq'

            v = self.parse(val)
            if v is False or v is True or v is None:
                if op == 'eq':
                    return expr.is_(v)
                if op == 'ne':
                    return expr.isnot(v)
                raise Error('invalid operator: {}'.format(op))
            return getattr(operators, op)(expr, v)


class BoolClause(FilterClause):
    data_type = Bool
    operators = (OPERATOR_NONE, OPERATOR_EQ)

    @staticmethod
    def parse(val):
        return parse_bool(val)


class IntegerClause(FilterClause):
    data_type = Integer
    operators = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE,
                 OPERATOR_GT, OPERATOR_GE, OPERATOR_LT, OPERATOR_LE)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_int(val)


class FloatClause(FilterClause):
    data_type = Float
    operators = (OPERATOR_GT, OPERATOR_GE, OPERATOR_LT, OPERATOR_LE)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_float(val)


class DateClause(FilterClause):
    data_type = Date
    operators = (OPERATOR_GT, OPERATOR_LT)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_date(val)


class TimeClause(FilterClause):
    data_type = Time
    operators = (OPERATOR_GT, OPERATOR_LT)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_time(val)


class DateTimeClause(FilterClause):
    data_type = DateTime
    operators = (OPERATOR_GT, OPERATOR_LT)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_datetime(val)


class StringClause(FilterClause):
    data_type = String
    operators = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)


class Filter:

    def __init__(self, where=None, *from_items):
        self.where = list(where) if where is not None else list()
        self.from_items = list(from_items)
        self.having = list()

    def __bool__(self):
        return any((self.where, self.having, self.from_items))

    def add(self, attr, op, val):
        clause = attr.filter_clause.get(attr.expr, op, val)
        if attr.is_aggregate():
            self.having.append(clause)
        else:
            self.where.append(clause)

    def add_custom(self, name, custom_clause):
        if is_clause(custom_clause):
            self.where.append(custom_clause)
        else:
            try:
                if len(custom_clause) == 2 and is_clause(custom_clause[0]) \
                        and all(is_from_item(fi for fi in custom_clause[1])):
                    self.where.append(custom_clause[0])
                    self.from_items.extend(custom_clause[1])
                else:
                    raise TypeError
            except TypeError:
                raise Error('filter:{} | expected a where clause and a sequence '
                            'of from items'.format(name))
