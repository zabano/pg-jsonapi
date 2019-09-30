import re

import sqlalchemy as sa

from jsonapi.fields import Aggregate
from .util import *


class FilterClause:

    def __init__(self, **options):

        operators = list()
        for op in options.pop('operators', tuple()):
            if op not in OPERATORS:
                raise ValueError('[FilterExpression] invalid op: {}'.format(op))
            operators.append(op)
        self.operators = tuple(operators)

        self.decoder = options.pop('decoder', None)
        if self.decoder is None:
            self.decoder = lambda x: x

        self.multiple = options.pop('multiple', None)

    def parse_values(self, val):
        if any(symbol in val for symbol in MODIFIERS):
            values = list()
            for v in val.split(','):
                match = re.match('({})?(\w+)'.format('|'.join(MODIFIERS)), v)
                if match:
                    mod = '=' if not match[1] else match[1]
                    values.append((mod, self.decoder(match[2])))
            return values
        else:
            return [('=', self.decoder(v)) for v in val.split(',')]

    def __call__(self, expr, op, val):

        #
        # multiple values
        #
        if ',' in val:
            if self.multiple is None:
                raise Error('multiple values not supported')
            if op != '' and op not in self.multiple.keys():
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
                return sa.or_(*expressions)

        #
        # single values
        #
        else:
            if op not in self.operators:
                raise Error('invalid operator: {}'.format(op))
            if op == '':
                op = 'eq'

            v = self.decoder(val)
            if v in (True, False, None):
                if op == 'eq':
                    return expr.is_(v)
                if op == 'ne':
                    return expr.isnot(v)
                raise Error('invalid operator: {}'.format(op))
            return getattr(operator, op)(expr, v)


class Filter:

    def __init__(self, where=None, *from_items):
        self.where = list(where) if where is not None else list()
        self.from_items = tuple(from_items)
        self.having = list()

    def add(self, attr, op, val):

        if attr.name == 'id' or attr.is_int():
            fc = FilterClause(operators=('', 'eq', 'ne', 'gt', 'lt', 'ge', 'le'),
                              decoder=parse_int,
                              multiple=dict(eq=True, ne=False))
        elif attr.is_float():
            fc = FilterClause(operators=('gt', 'lt', 'ge', 'le'), decoder=parse_float)
        elif attr.is_bool():
            fc = FilterClause(operators=('',), decoder=parse_bool, multiple=dict(eq=False))
        elif attr.is_datetime():
            fc = FilterClause(operators=('gt', 'lt'), decoder=parse_datetime)
        elif attr.is_date():
            fc = FilterClause(operators=('gt', 'lt'), decoder=parse_date)
        elif attr.is_time():
            fc = FilterClause(operators=('gt', 'lt'), decoder=parse_time)
        else:
            fc = FilterClause(operators=('', 'eq', 'ne'), multiple=dict(eq=False, ne=False))

        clause = fc(attr.expr, op, val)
        if isinstance(attr, Aggregate):
            self.having.append(clause)
        else:
            self.where.append(clause)
