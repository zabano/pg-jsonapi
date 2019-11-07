import enum
from collections import OrderedDict
from functools import reduce

from sqlalchemy.exc import NoForeignKeysError
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from sqlalchemy.sql.schema import Column, Table
from sqlalchemy.sql import Alias, Selectable, Join

from jsonapi.exc import APIError, Error


class Cardinality(enum.IntEnum):
    """
    The cardinality of a relationship between two models.

        - ONE_TO_ONE
        - MANY_TO_ONE
        - ONE_TO_MANY
        - MANY_TO_MANY
    """
    ONE_TO_ONE = 0
    MANY_TO_ONE = 1
    ONE_TO_MANY = 2
    MANY_TO_MANY = 3


ONE_TO_ONE = Cardinality.ONE_TO_ONE
MANY_TO_ONE = Cardinality.MANY_TO_ONE
ONE_TO_MANY = Cardinality.ONE_TO_MANY
MANY_TO_MANY = Cardinality.MANY_TO_MANY


class PathJoin:

    def __init__(self):
        self.from_items = list()
        self.distinct = False

    def load(self, model, path):
        field = None
        for name in path:
            if name not in model.fields.keys():
                raise APIError('{}.{} | does not exist'.format(model.name, name), model)
            field = model.fields[name]
            if field.is_relationship():
                self.from_items.extend(field.get_from_items())
                if field.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
                    self.distinct = True
                model = field.model
        assert field is not None
        return field


class OrderBy(PathJoin):

    def __init__(self, model=None, *args):
        super().__init__()
        self.order_by = list()
        self.group_by = list()

        if model:
            for arg in args:
                self.add(model, arg)

    def __bool__(self):
        return bool(self.order_by)

    def __len__(self):
        return len(self.order_by)

    def __iter__(self):
        return iter(self.order_by)

    def add(self, model, arg):
        field = self.load(model, arg.path)
        if field.is_relationship():
            attr = field.model.fields['id']
            expr = getattr(attr.expr, 'desc' if arg.desc else 'asc')
            self.order_by.append(expr().nullslast())
        else:
            expr = getattr(field.expr, 'desc' if arg.desc else 'asc')
            self.order_by.append(expr().nullslast())
            if field.is_aggregate():
                self.from_items.extend(field.rel.get_from_items())
                if field.rel.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
                    self.distinct = True
            else:
                self.group_by.append(field.expr)


class FromItem:
    """
    Represent a single item in the FROM list of a SELECT query.

    Each :class:`FromItem` item represents a table (or an alias to a table).
    A :class:`FromItem` object may include an :attr:`onclause` used when
    joining with other :class:`FromItem` objects. If the :attr:`left` flag is
    set, an outer left join is performed.

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

    def __init__(self, table, **kwargs):
        """
        :param table: an SQLAlchemy Table or Alias object
        :param onclause: an onclause join expression (optional)
        :param left: if set perform outer left join (optional)
        """
        self.table = table
        self.onclause = kwargs.get('onclause', None)
        self.left = bool(kwargs.get('left', False))

        if not isinstance(self.table, Selectable):
            raise Error('[FromItem] invalid "table" argument: {}'.format(self.table))

        if self.onclause is not None:
            if not is_clause(self.onclause):
                raise Error('[FromItem] invalid "onclause" argument: {}'.format(
                    self.onclause))

    @property
    def name(self):
        """
        A unique string identifier (the name of the table, or the table alias).
        """
        table = get_left(self.table) if isinstance(self.table, Join) else self.table
        return '{}.{}'.format(table.schema, table.name) if table.schema else table.name

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.name)

    def __str__(self):
        return self.name


class FromClause:
    """
    Represent the FROM clause of a SELECT query.
    A :class:`FromClause` object is a sequence of :class:`FromItem` objects.

    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> fc = FromClause(users_t)
    >>> fc.add(FromItem(user_names_t, left=True))
    >>> len(fc)
    2
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
        items = [self.value(item) for item in from_items]
        self._from_items = OrderedDict([(i.name, i) for i in items])

    def add(self, *items):
        for item in items:
            if item.name not in self._from_items \
                    or not (isinstance(item.table, Join) or isinstance(self._from_items[item.name], Join)):
                self._from_items[item.name] = self.value(item)

    def __len__(self):
        return len(self._from_items)

    def __iter__(self):
        return iter(self._from_items.values())

    def __call__(self):
        items = list(self._from_items.values())
        tables = [items[0].table] + items[1:]
        try:
            return reduce(lambda l, r: l.join(r.table, onclause=r.onclause, isouter=True), tables)
        except NoForeignKeysError:
            left = tables.pop(0)
            n = len(tables)
            for i in range(n):
                for j in range(len(tables)):
                    right = tables[j]
                    try:
                        left = left.join(right.table, onclause=right.onclause, isouter=True)
                    except NoForeignKeysError:
                        pass
                    else:
                        tables.pop(j)
                        break
            return left

    def get_column(self, col):
        if isinstance(col, str):
            for c in self().columns.values():
                if c.name == col:
                    return c
        elif isinstance(col, Column):
            for c in self().columns.values():
                if get_table_name(c.table) == get_table_name(col.table) and c.name == col.name:
                    return c

    @staticmethod
    def value(item):
        if not isinstance(item, (Table, Alias, FromItem)):
            raise Error('FromClause | invalid item: {!r}')
        return item if isinstance(item, FromItem) else FromItem(item)

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, ', '.join(name for name in self._from_items.keys()))

    def __str__(self):
        if len(self) > 0:
            return str(self().compile())
        return ''


def get_table(table_or_alias):
    if hasattr(table_or_alias, 'element'):
        return get_table(table_or_alias.element)
    return table_or_alias


def get_table_name(table_or_alias):
    if hasattr(table_or_alias, 'element'):
        return get_table_name(table_or_alias.element)
    return table_or_alias.name


def get_left(join):
    if hasattr(join, 'left'):
        return get_left(join.left)
    return join


def get_primary_key(table):
    """
    Get table primary key column.

    .. note::

        Assumes a simple (non-composite) key and returns the first column.

    :param table: SQLAlchemy Table object
    :return: the primary key column
    """
    try:
        return table.primary_key.columns.values()[0]
    except AttributeError:
        return table.primary_key[0]


def is_from_item(from_item):
    return isinstance(from_item, (Table, Alias, FromItem))


def is_clause(clause):
    return isinstance(clause, (BinaryExpression, BooleanClauseList))
