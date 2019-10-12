import enum
import re

from sqlalchemy.sql import and_, operators, or_

from jsonapi.exc import Error, ModelError
from .table import FromItem, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE, get_foreign_key_pair, is_clause, \
    is_from_item

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


class Filter:

    def __init__(self, where=None, *from_items):
        self.where = list(where) if where is not None else list()
        self.having = list()
        self.from_items = list(from_items)
        self.from_items_last = list()
        self.distinct = False

    def __bool__(self):
        return any((self.where, self.having, self.from_items))

    @staticmethod
    def _rel_from_items(rel):
        if rel.cardinality == ONE_TO_ONE:
            onclause = rel.model.primary_key == rel.parent.primary_key
        elif rel.cardinality == ONE_TO_MANY:
            onclause = rel.model.get_db_column(rel.ref) == rel.parent.primary_key
        elif rel.cardinality == MANY_TO_ONE:
            onclause = rel.model.primary_key == rel.parent.get_db_column(rel.ref)
        else:
            ref_col_model, ref_col_parent = get_foreign_key_pair(rel.ref, rel.model)
            return [FromItem(rel.ref,
                             onclause=ref_col_parent == rel.parent.primary_key,
                             left=True),
                    FromItem(rel.model.primary_key.table,
                             onclause=rel.model.primary_key == ref_col_model,
                             left=True)]
        return [FromItem(rel.model.primary_key.table, onclause=onclause, left=True)]

    def add(self, field, arg):
        if field.is_relationship():

            attr_name = arg.attr_name if arg.attr_name else 'id'
            if attr_name not in field.model.fields.keys():
                raise ModelError('field: {} does not exist'.format(attr_name), field.model)
            attr = field.model.fields[attr_name]
            filter_clause = attr.filter_clause.get(attr.expr, arg.operator, arg.value)
            self.from_items.extend(self._rel_from_items(field))
            if attr.is_aggregate():
                self.from_items_last.extend(attr.from_items.get(field.model.name, list()))
                self.having.append(filter_clause)
            else:
                self.where.append(filter_clause)
        else:
            clause = field.filter_clause.get(field.expr, arg.operator, arg.value)
            if field.is_aggregate():
                self.from_items.extend(self._rel_from_items(field.rel))
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

        self.data_type = data_type

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

    def check_operator(self, op):
        if not isinstance(op, Operator):
            raise ValueError('[{}}] invalid operator: {!r}'.format(op, self.__class__.__name__))

    def has_operator(self, op, multiple=False):
        return op in (o.value for o in (self.multiple if multiple else self.operators))

    def parse_values(self, val):
        if any(symbol in val for symbol in MODIFIERS):
            values = list()
            for v in val.split(','):
                match = re.match('({})?(\w+)'.format('|'.join(MODIFIERS)), v)
                if match:
                    mod = '=' if not match[1] else match[1]
                    values.append((mod, self.data_type.parse(match[2])))
            return values
        else:
            return [('=', self.data_type.parse(v)) for v in val.split(',')]

    def get(self, expr, op, val):

        #
        # multiple values
        #
        if ',' in val:
            if not self.has_operator(op, multiple=True):
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
            if not self.has_operator(op):
                raise Error('invalid operator: {}'.format(op))
            if op == '':
                op = 'eq'

            v = self.data_type.parse(val)
            if v is False or v is True or v is None:
                if op == 'eq':
                    return expr.is_(v)
                if op == 'ne':
                    return expr.isnot(v)
                raise Error('invalid operator: {}'.format(op))
            return getattr(operators, op)(expr, v)
