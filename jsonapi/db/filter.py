import enum
import re

from sqlalchemy.sql import operators, or_

from jsonapi.fields import Aggregate
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
    operators = tuple()
    multiple = tuple()

    def __init__(self):

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

    def get_clause(self, expr, op, val):

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
    operators = (OPERATOR_NONE, OPERATOR_EQ)

    @staticmethod
    def parse(val):
        return parse_bool(val)


class IntegerClause(FilterClause):
    operators = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE,
                 OPERATOR_GT, OPERATOR_GE, OPERATOR_LT, OPERATOR_LE)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_int(val)


class FloatClause(FilterClause):
    operators = (OPERATOR_GT, OPERATOR_GE, OPERATOR_LT, OPERATOR_LE)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_float(val)


class DateClause(FilterClause):
    operators = (OPERATOR_GT, OPERATOR_LT)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_date(val)


class TimeClause(FilterClause):
    operators = (OPERATOR_GT, OPERATOR_LT)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_time(val)


class DateTimeClause(FilterClause):
    operators = (OPERATOR_GT, OPERATOR_LT)
    multiple = (OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE)

    @staticmethod
    def parse(val):
        return parse_datetime(val)


class StringClause(FilterClause):
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

        if attr.is_bool():
            fc = BoolClause()
        elif attr.name == 'id' or attr.is_int():
            fc = IntegerClause()
        elif attr.is_float():
            fc = FloatClause()
        elif attr.is_date():
            fc = DateClause()
        elif attr.is_time():
            fc = TimeClause()
        elif attr.is_datetime():
            fc = DateTimeClause()
        else:
            fc = StringClause()

        clause = fc.get_clause(attr.expr, op, val)
        if isinstance(attr, Aggregate):
            self.having.append(clause)
        else:
            self.where.append(clause)
