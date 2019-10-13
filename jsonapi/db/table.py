import enum
from collections.abc import MutableSequence
from functools import reduce

from sqlalchemy.exc import NoForeignKeysError
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import Alias

from jsonapi.exc import APIError, Error


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


class OrderBy:

    def __init__(self):
        self.exprs = list()
        self.from_items = list()
        self.group_by = list()
        self.distinct = False

    def __bool__(self):
        return bool(self.exprs)

    def add(self, field, arg):
        if field.is_relationship():
            attr_name = arg.attr_name if arg.attr_name else 'id'
            if attr_name not in field.model.fields.keys():
                raise APIError('sort: {}.{} | does not exist'.format(field.name, attr_name),
                               field.model)
            attr = field.model.fields[attr_name]
            self.from_items.extend(get_from_items(field))
            self.exprs.append(getattr(attr.expr, 'desc' if arg.desc else 'asc')().nullslast())
            if not attr.is_aggregate():
                self.group_by.append(attr.expr)
            if field.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
                self.distinct = True
        else:
            self.exprs.append(getattr(field.expr, 'desc' if arg.desc else 'asc')().nullslast())
            if field.is_aggregate():
                self.from_items.extend(get_from_items(field.rel))
                if field.rel.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
                    self.distinct = True
            else:
                self.group_by.append(field.expr)


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

    def __init__(self, table, **kwargs):
        """
        :param table: an SQLAlchemy Table or Alias object
        :param onclause: an onclause join expression (optional)
        :param left: if set perform outer left join, otherwise perform inner join (optional)
        """
        self.table = table
        self.onclause = kwargs.get('onclause', None)
        self.left = bool(kwargs.get('left', False))

        if not isinstance(self.table, (Table, Alias)):
            raise Error('[FromItem] invalid "table" argument: {}'.format(self.table))

        if self.onclause is not None:
            if not is_clause(self.onclause):
                raise Error('[FromItem] invalid "onclause" argument: {}'.format(self.onclause))

    @property
    def name(self):
        """
        A unique string identifier (the name of the table, or the table alias).
        """
        return self.table.name

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
        self._from_items = [self.value(item) for item in from_items]

    def __len__(self):
        return len(self._from_items)

    def __getitem__(self, index):
        return self._from_items[index]

    def __setitem__(self, index, item):
        from_item = self._from_items[index]
        if item.name == from_item.table.name or self.is_valid(item):
            self._from_items[index] = self.value(item)

    def __delitem__(self, index):
        del self._from_items[index]

    def insert(self, index, item):
        if self.is_valid(item):
            self._from_items.insert(index, self.value(item))

    def __call__(self):
        tables = [self._from_items[0].table] + self._from_items[1:]
        try:
            return reduce(lambda l, r: l.join(r.table, onclause=r.onclause, isouter=r.left), tables)
        except NoForeignKeysError:
            left = tables.pop(0)
            n = len(tables)
            for i in range(n):
                for j in range(len(tables)):
                    right = tables[j]
                    try:
                        left = left.join(right.table, onclause=right.onclause, isouter=right.left)
                    except NoForeignKeysError:
                        pass
                    else:
                        tables.pop(j)
                        break
            return left

    def get_column(self, name):
        for col in self().columns:
            if col.name == name:
                return col

    @staticmethod
    def value(item):
        return item if isinstance(item, FromItem) else FromItem(item)

    def keys(self):
        return (from_item.name for from_item in self._from_items)

    def is_valid(self, item):
        return isinstance(item, (Table, Alias, FromItem)) and item.name not in self.keys()

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, ', '.join(
            from_item.name for from_item in self._from_items))

    def __str__(self):
        if len(self) > 0:
            return self._from_items[0].table.name if len(self) == 1 else str(self().compile())
        return ''


def get_table(table_or_alias):
    if hasattr(table_or_alias, 'element'):
        return get_table(table_or_alias.element)
    return table_or_alias


def get_table_name(table_or_alias):
    if hasattr(table_or_alias, 'element'):
        return get_table_name(table_or_alias.element)
    return table_or_alias.name


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


def get_foreign_key_pair(model, model_ref, parent_ref):
    tb = get_table(model.primary_key.table)
    for table in tb.metadata.tables.values():
        ref_names = list(fk.parent.name for fk in table.foreign_keys)
        if model_ref in ref_names and parent_ref in ref_names:
            return table.c[model_ref], table.c[parent_ref]
    raise Error('foreign key pair not found: {!r}'.format((model_ref, parent_ref)))


def get_from_items(rel):
    if rel.cardinality == Cardinality.ONE_TO_ONE:
        onclause = rel.model.primary_key == rel.parent.primary_key
    elif rel.cardinality == Cardinality.ONE_TO_MANY:
        onclause = rel.model.get_expr(rel.ref) == rel.parent.primary_key
    elif rel.cardinality == Cardinality.MANY_TO_ONE:
        onclause = rel.model.primary_key == rel.parent.get_expr(rel.ref)
    else:
        ref_col, parent_col = get_foreign_key_pair(rel.model, *rel.ref)
        return [FromItem(parent_col.table,
                         onclause=parent_col == rel.parent.primary_key,
                         left=True),
                FromItem(rel.model.primary_key.table,
                         onclause=rel.model.primary_key == ref_col,
                         left=True)]
    return [FromItem(rel.model.primary_key.table, onclause=onclause, left=True)]


def is_from_item(from_item):
    return isinstance(from_item, (Table, Alias, FromItem))


def is_clause(clause):
    return isinstance(clause, (BinaryExpression, BooleanClauseList))
