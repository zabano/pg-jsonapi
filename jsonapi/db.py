"""
Database Utilities.

The :mod:`jsonapi.db` module provides an interface to the database layer.
"""

import enum
from collections.abc import MutableSequence
from copy import copy
from functools import reduce

import sqlalchemy as sa
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.elements import BooleanClauseList
from sqlalchemy.sql.selectable import Alias

from jsonapi.exc import Error
from jsonapi.fields import Field, Aggregate


def get_primary_key(table):
    """
    Get table primary key column.

    .. note::

        Assumes a simple (non-composite) key and returns the first column.

    :param table: SQLAlchemy Table object
    :return: the primary key column
    """
    return table.primary_key.columns.values()[0]


class Cardinality(enum.Enum):
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
        return reduce(lambda l, r: l.join(r.table, onclause=r.onclause, isouter=r.left), tables)

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
        self._model = model

    def _select_from(self, *additional):
        from_clause = copy(self._model.from_clause)
        from_clause.extend(additional)
        for field in self._model.schema_fields:
            if isinstance(field, Aggregate):
                from_clause.append(FromItem(field.from_alias, left=True))
        return from_clause()

    def _is_aggregate(self):
        return any(isinstance(field, Aggregate) for field in self._model.schema_fields)

    def _col_list(self, group_by=False):
        return [field.expr.label(field.name) for field in self._model.schema_fields if
                isinstance(field, Field if group_by else (Field, Aggregate))]

    @property
    def columns(self):
        return self._select_from().c

    def _group_by(self, query, *columns):
        if self._is_aggregate():
            query = query.group_by(*[*self._col_list(group_by=True), *columns])
        return query

    def _sort_by(self, query):
        return query.order_by(*[getattr(self._model.attributes[name].expr,
                                        'desc' if desc else 'asc')().nullslast() for
                                name, desc in self._model.args.sort.items()])

    def get(self, resource_id):
        query = sa.select(self._col_list()).select_from(self._select_from()).where(
            self._model.primary_key == resource_id)
        query = self._group_by(query)
        return query

    def all(self):
        query = sa.select(self._col_list()).select_from(self._select_from())
        query = self._group_by(query)
        query = self._sort_by(query)
        return query

    def related(self, resource_id, rel):
        fkey_column = rel.fkey.parent
        pkey_column = get_primary_key(fkey_column.table)
        where_col = pkey_column if rel.cardinality in (ONE_TO_ONE, MANY_TO_ONE) \
            else fkey_column
        query = sa.select(self._col_list()).select_from(self._select_from(fkey_column.table)).where(
            where_col == resource_id)
        query = self._group_by(query)
        if rel.cardinality in (ONE_TO_MANY, MANY_TO_MANY):
            query = self._sort_by(query)
        return query

    def included(self, rel, id_list):
        where_col = get_primary_key(rel.fkey.parent.table) \
            if rel.cardinality is MANY_TO_ONE else rel.fkey.parent
        query = sa.select(self._col_list() + [where_col.label('parent_id')]).select_from(
            self._select_from(rel.fkey.parent.table)).where(where_col.in_(id_list))
        query = self._group_by(query, where_col)
        return query
