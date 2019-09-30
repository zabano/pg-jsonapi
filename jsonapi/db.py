"""
Database Utilities.

The :mod:`jsonapi.db` module provides an interface to the database layer.
"""

import enum
import operator
import re
from collections.abc import MutableSequence
from copy import copy
from datetime import datetime as dt
from functools import reduce

import sqlalchemy as sa
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from sqlalchemy.sql.selectable import Alias

from jsonapi.exc import APIError, Error, ModelError
from jsonapi.fields import Aggregate, Field

SQL_PARAM_LIMIT = 10000

DATETIME_FORMATS = ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y-%m')
DATE_FORMATS = ('%Y-%m-%d', '%Y-%m')
TIME_FORMATS = ('%H:%M:%SZ', '%H:%M')

TRUE_VALUES = ('t', 'true', 'on', '1')
FALSE_VALUES = ('f', 'false', 'off', '0')
NULL_VALUES = ('null', 'none', 'na')

OPERATORS = ('', 'eq', 'ne', 'gt', 'ge', 'lt', 'le')
MODIFIERS = {'=': operator.eq, '<>': operator.ne, '!=': operator.ne,
             '>=': operator.ge, '<=': operator.le, '>': operator.gt, '<': operator.lt}


def get_primary_key(table):
    """
    Get table primary key column.

    .. note::

        Assumes a simple (non-composite) key and returns the first column.

    :param table: SQLAlchemy Table object
    :return: the primary key column
    """
    return table.primary_key.columns.values()[0]


class Cardinality(enum.IntEnum):
    """
    The cardinality of a relationship between two models.
    """

    ONE_TO_ONE = 0
    MANY_TO_ONE = 1
    ONE_TO_MANY = 2
    MANY_TO_MANY = 3


ONE_TO_ONE = Cardinality.ONE_TO_ONE
MANY_TO_ONE = Cardinality.MANY_TO_ONE
ONE_TO_MANY = Cardinality.ONE_TO_MANY
MANY_TO_MANY = Cardinality.MANY_TO_MANY


def parse_bool(val):
    if val.lower() in NULL_VALUES:
        return
    if val.lower() not in TRUE_VALUES and val.lower() not in FALSE_VALUES:
        raise Error('invalid value: {}'.format(val))
    return val.lower() in TRUE_VALUES


def parse_int(val):
    if val.lower() in NULL_VALUES:
        return
    try:
        return int(val)
    except ValueError:
        raise Error('invalid value: {}'.format(val))


def parse_float(val):
    if val.lower() in NULL_VALUES:
        return
    try:
        return float(val)
    except ValueError:
        raise Error('invalid value: {}'.format(val))


def parse_date(val):
    if val.lower() in NULL_VALUES:
        return
    fmt = {len(fmt) + 2: fmt for fmt in DATE_FORMATS}
    if len(val) not in fmt:
        raise Error('invalid value: {}'.format(val))
    return dt.strptime(val, fmt[len(val)])


def parse_time(val):
    if val.lower() in NULL_VALUES:
        return
    fmt = {len(fmt): fmt for fmt in TIME_FORMATS}
    if len(val) not in fmt:
        raise Error('invalid value: {}'.format(val))
    return dt.strptime(val, fmt[len(val)])


def parse_datetime(val):
    if val.lower() in NULL_VALUES:
        return
    fmt = {len(fmt) + 2: fmt for fmt in DATETIME_FORMATS}
    if len(val) not in fmt:
        raise Error('invalid value: {}'.format(val))
    return dt.strptime(val, fmt[len(val)])


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


class FromItem:
    """
    Represent a single item in the FROM list of a SELECT query.

    Each :class:`FromItem` item represents a table (or an alias to a table).
    A :class:`FromItem` object may include an :attr:`onclause` used when joining
    with other :class:`FromItem` objects. If the :attr:`left` flag is set, an outer left join is
    performed.

    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> a = FromItem(user_names_t)
    >>> b = FromItem(user_names_t, users_t.c.id == user_names_t.c.id)
    >>> c = FromItem(user_names_t, users_t.c.id == user_names_t.c.id, left=True)
    >>> d = FromItem(user_names_t, left=True)
    >>> b
    <FromItem(user_names)>
    >>> b.onclause
    <sqlalchemy.sql.elements.BinaryExpression object at ...>
    >>> b.left
    False
    >>> b.name
    user_names
    >>> print(b)
    user_names

    """

    def __init__(self, table, onclause=None, left=False):
        """
        :param table: an SQLAlchemy Table or Alias object
        :param onclause: an onclause join expression (optional)
        :param left: if set perform outer left join, otherwise perform inner join (optional)
        """
        self.table = table
        self.onclause = onclause
        self.left = bool(left)

        if not isinstance(table, (sa.Table, Alias)):
            raise Error('[FromItem] invalid "table" argument: {}'.format(table))

        if onclause is not None:
            if not isinstance(onclause, (BinaryExpression, BooleanClauseList)):
                raise Error('[FromItem] invalid "onclause" argument: {}'.format(onclause))

    @property
    def name(self):
        """
        A unique string identifier (the name of the table, or the table alias).
        """
        return self.table.name if isinstance(self.table, (Alias, sa.Table)) else \
            self.element.table.name

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.name)

    def __str__(self):
        return self.name


class FromClause(MutableSequence):
    """
    Represent the FROM clause of a SELECT query.
    A :class:`FromClause` object is a sequence of :class:`FromItem` objects.
    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> fc = FromClause(users_t)
    >>> fc.append(FromItem(user_names_t, left=True))
    >>> len(fc)
    2
    >>> fc[0], (fc[1], fc[1].left)
    (<FromItem(users)>, (<FromItem(user_names)>, True))
    >>> fc
    <FromClause(users, user_names)>
    >>> print(fc)
    public.users LEFT OUTER JOIN public.user_names ON public.users.id = public.user_names.id
    >>> fc()
    <sqlalchemy.sql.selectable.Join at ...; Join object on users(...) and user_names(...)>
    >>> print(fc())
    public.users LEFT OUTER JOIN public.user_names ON public.users.id = public.user_names.id
    """

    def __init__(self, *from_items):
        """
        :param from_items: a variable length list of FROM items, tables, or aliases.
        """
        self._from_items = [self._value(item) for item in from_items]

    def __len__(self):
        return len(self._from_items)

    def __getitem__(self, index):
        return self._from_items[index]

    def __setitem__(self, index, item):
        from_item = self._from_items[index]
        if self._name(item) == from_item.table.name or self._is_valid(item):
            self._from_items[index] = self._value(item)

    def __delitem__(self, index):
        del self._from_items[index]

    def __call__(self):
        tables = [self._from_items[0].table] + self._from_items[1:]
        try:
            return reduce(lambda l, r: l.join(r.table, onclause=r.onclause, isouter=r.left), tables)
        except sa.exc.NoForeignKeysError:
            left = tables.pop(0)
            n = len(tables)
            for i in range(n):
                for j in range(len(tables)):
                    right = tables[j]
                    try:
                        left = left.join(right.table, onclause=right.onclause, isouter=right.left)
                    except sa.exc.NoForeignKeysError:
                        pass
                    else:
                        tables.pop(j)
                        break
            return left

    @staticmethod
    def _name(item):
        return item.name

    @staticmethod
    def _value(item):
        return item if isinstance(item, FromItem) else FromItem(item)

    def _keys(self):
        return (from_item.table.name for from_item in self._from_items)

    def _is_valid(self, item):
        return isinstance(item, (sa.Table, Alias, FromItem)) and self._name(
            item) not in self._keys()

    def insert(self, index, item):
        if self._is_valid(item):
            self._from_items.insert(index, self._value(item))

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, ', '.join(
            from_item.name for from_item in self._from_items))

    def __str__(self):
        if len(self) > 0:
            return self._from_items[0].table.name if len(self) == 1 else str(self().compile())
        return ''


INCLUDE_BATCH_SIZE = 10000


class Query:
    """
    Represents a SELECT query.
    """

    def __init__(self, model):
        self.model = model

    def is_aggregate(self):
        return any(isinstance(field, Aggregate) for field in self.model.schema_fields)

    def col_list(self, group_by=False, search=None):
        col_list = [field.expr.label(field.name) for field in self.model.schema_fields if
                    isinstance(field, Field if group_by else (Field, Aggregate))]
        if self.model.search is not None and search is not None:
            col_list.append(self.rank_column(search))
        return col_list

    def from_obj(self, *additional):
        from_clause = copy(self.model.from_clause)
        from_clause.extend(additional)
        for field in self.model.schema_fields:
            if isinstance(field, Aggregate):
                for from_item in field.from_items:
                    from_clause.append(from_item)
        return from_clause()

    @property
    def columns(self):
        return self.from_obj().c

    def rank_column(self, search):
        if self.model.search is not None and search is not None:
            return sa.func.ts_rank_cd(
                self.model.search.c.tsvector, sa.func.to_tsquery(search)).label('_ts_rank')

    def group_by(self, query, *columns):
        if self.is_aggregate():
            query = query.group_by(*[*self.col_list(group_by=True), *columns])
        return query

    def sort_by(self, query, search=None):
        if self.model.search is not None and search is not None:
            return query.order_by(self.rank_column(search).desc())
        order_by = list()
        for name, desc in self.model.args.sort.items():
            try:
                expr = self.model.attributes[name].expr
            except KeyError:
                raise APIError('column does not exist: {}'.format(name), self.model)
            else:
                order_by.append(getattr(expr, 'desc' if desc else 'asc')().nullslast())
        return query.order_by(*order_by)

    def check_access(self, query):

        if self.model.access is None:
            return query

        if not hasattr(self.model, 'user'):
            raise ModelError('"user" not defined for protected model', self.model)

        return query.where(self.model.access(
            self.model.primary_key, self.model.user.id if self.model.user else None))

    def _search(self, query, search):
        if self.model.search is None or search is None:
            return query
        query = query.where(self.model.search.c.tsvector.match(search))
        return query

    def exists(self, resource_id):
        return sa.select([sa.exists(sa.select([self.model.primary_key]).where(
            self.model.primary_key == resource_id))])

    def get(self, resource_id):
        query = sa.select(from_obj=self.from_obj(),
                          columns=self.col_list(),
                          whereclause=self.model.primary_key == resource_id)
        query = self.group_by(query)
        if self.model.access is not None:
            query = self.check_access(query)
        return query

    def all(self, filter_by=None, paginate=True, count=False, search=None):

        search_t = self.model.search
        from_obj = self.from_obj(search_t) if search is not None else self.from_obj()
        query = sa.select(columns=self.col_list(search=search), from_obj=from_obj)
        query = self.group_by(query)

        if not count:
            query = self.sort_by(query, search)

        if filter_by is not None:
            if isinstance(filter_by, Filter):
                if filter_by.where:
                    query = query.where(sa.and_(*filter_by.where))
                if filter_by.having:
                    query = query.having(sa.and_(filter_by.having))
            else:
                return query.where(filter_by)

        query = self.check_access(query)

        if paginate and self.model.args.limit is not None:
            query = query.offset(self.model.args.offset).limit(self.model.args.limit)

        query = self._search(query, search)

        return query.alias('count').count() if count else query

    def search(self, term):
        search_t = self.model.search
        query = sa.select(columns=[self.model.primary_key, self.rank_column(term)],
                          from_obj=self.from_obj(search_t))
        query = self._search(query, term)
        return self.check_access(query)

    def related(self, resource_id, rel):
        pkey_column = get_primary_key(rel.fkey.parent.table)
        where_col = pkey_column if rel.cardinality in (ONE_TO_ONE, MANY_TO_ONE) \
            else rel.fkey.parent
        query = sa.select(columns=self.col_list(),
                          from_obj=self.from_obj(
                              FromItem(rel.fkey.parent.table,
                                       onclause=rel.fkey.column == rel.fkey.parent,
                                       left=True)),
                          whereclause=where_col == resource_id)
        query = self.group_by(query)
        if rel.cardinality in (ONE_TO_MANY, MANY_TO_MANY):
            query = self.sort_by(query)
        query = self.check_access(query)
        return query

    def included(self, rel, id_list):
        where_col = get_primary_key(rel.fkey.parent.table) \
            if rel.cardinality is MANY_TO_ONE else rel.fkey.parent
        query = sa.select(columns=[*self.col_list(), where_col.label('parent_id')],
                          from_obj=self.from_obj(
                              FromItem(rel.fkey.parent.table,
                                       onclause=rel.fkey.column == rel.fkey.parent,
                                       left=True)))
        query = self.group_by(query, where_col)
        query = self.check_access(query)
        return (query.where(where_col.in_(x))
                for x in (id_list[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(id_list), SQL_PARAM_LIMIT)))
