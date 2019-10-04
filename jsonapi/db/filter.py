import enum
import re

from sqlalchemy.sql import operators, or_

from jsonapi.exc import Error
from jsonapi.datatypes import DataType, Bool, Integer, Float, String, Date, Time, DateTime
from .table import is_clause, is_from_item

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


class FilterClause:

    def __init__(self, data_type, *ops, **kwargs):

        if not isinstance(data_type, DataType):
            raise ValueError('[{}}] invalid data type: {!r}'.format(
                data_type, self.__name__))

        self.parse = data_type.parse

        for op in ops:
            self.check_operator(op)
        self.operators = tuple(set(ops))

        multiple = kwargs.get('multiple', None)
        if multiple:
            try:
                iter(multiple)
            except TypeError:
                self.check_operator(multiple)
                self.multiple = (multiple,)
            else:
                for op in multiple:
                    self.check_operator(op)
                self.multiple = tuple(set(multiple))

        data_type.filter_clause = self

    def check_operator(self, op):
        if not isinstance(op, Operator):
            raise ValueError('[{}}] invalid operator: {!r}'.format(op, self.__class__.__name__))

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


BoolClause = FilterClause(Bool, OPERATOR_NONE, OPERATOR_EQ)

IntegerClause = FilterClause(Integer, OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE,
                             OPERATOR_GT, OPERATOR_GE, OPERATOR_LT, OPERATOR_LE,
                             multiple=(OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE))

FloatClause = FilterClause(Float, OPERATOR_GT, OPERATOR_GE, OPERATOR_LT, OPERATOR_LE,
                           multiple=(OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE))

DateClause = FilterClause(Date, OPERATOR_GT, OPERATOR_LT,
                          multiple=(OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE))

TimeClause = FilterClause(Time, OPERATOR_GT, OPERATOR_LT,
                          multiple=(OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE))

DateTimeClause = FilterClause(DateTime, OPERATOR_GT, OPERATOR_LT,
                              multiple=(OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE))

StringClause = FilterClause(String, OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE,
                            multiple=(OPERATOR_NONE, OPERATOR_EQ, OPERATOR_NE))
