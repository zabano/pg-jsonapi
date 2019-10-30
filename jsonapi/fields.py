import marshmallow as ma
from sqlalchemy.sql import text, and_
from sqlalchemy.sql.schema import Column

from jsonapi.datatypes import DataType, Date, Integer
from jsonapi.db.table import Cardinality, FromItem, get_primary_key, is_clause
from jsonapi.exc import Error, ModelError
from jsonapi.registry import model_registry, schema_registry


class BaseField:
    """ The base class for all field types """

    def __init__(self, name, data_type=None):

        if data_type is not None and not isinstance(data_type, DataType):
            raise Error('invalid data type provided: "{}"'.format(data_type))

        self.name = name
        self.data_type = data_type
        self.expr = None
        self.exclude = False
        self.sort_by = False
        self.filter_clause = None

    def get_filter_clause(self):
        data_type = Integer if self.name == 'id' else self.data_type
        if data_type is not None:
            return data_type.filter_clause

    def is_aggregate(self):
        return isinstance(self, Aggregate)

    def is_relationship(self):
        return isinstance(self, Relationship)

    def get_ma_field(self):
        if isinstance(self, Relationship):
            return ma.fields.Nested(
                schema_registry['{}Schema'.format(self.model.name)](),
                many=self.cardinality in (Cardinality.ONE_TO_MANY,
                                          Cardinality.MANY_TO_MANY))
        if issubclass(self.data_type.ma_type, ma.fields.Date):
            return self.data_type.ma_type(format=DataType.FORMAT_DATE)
        if issubclass(self.data_type.ma_type, ma.fields.DateTime):
            return self.data_type.ma_type(format=DataType.FORMAT_DATETIME)
        return self.data_type.ma_type()

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.name)


class Field(BaseField):
    """
    Basic field type, which maps to a database table column or a column expression.

    >>> from jsonapi.datatypes import Date
    >>> from jsonapi.tests.db import users_t
    >>>
    >>> Field('email')
    >>> Field('email-address', users_t.c.email)
    >>> Field('name', lambda c: c.first + ' ' + c.last)
    >>> Field('created-on', data_type=Date)
    """

    def __init__(self, name, col=None, data_type=None):
        """
        :param str name: a unique field name
        :param lambda func: a lambda function that accepts a ColumnCollection (optional)
        :param DataType data_type: defaults to String (optional)
        """
        super().__init__(name, data_type=data_type)
        self.col = col

    def load(self, model):
        if self.name == 'id':
            self.expr = model.primary_key
        elif isinstance(self.col, Column):
            self.expr = model.get_expr(self.col)
        elif self.col is not None:
            self.expr = self.col(model.rec)
        else:
            self.expr = model.get_expr(self.name)
        if self.data_type is None:
            self.data_type = DataType.get(self.expr)
        self.filter_clause = self.get_filter_clause()


class Aggregate(BaseField):
    """
    Represents an aggregate field (e.g. count, max, etc.)

    To define an aggregate field, an aggregate expression must be provided,
    along with one or more from items to add to the model's from clause.
    """

    def __init__(self, name, rel_name, func, col=None, data_type=None):
        """
        :param str name: field name
        :param rel_name: relationship name
        :param func: SQLAlchemy aggregate function (ex. func.count)
        :param DataType data_type: one of the supported data types (optional)
        """
        super().__init__(name, data_type=data_type)
        self.func = func
        self.col = col
        self.rel_name = rel_name
        self.rel = None
        self.from_items = dict()

    def load(self, model):
        self.rel = model.relationship(self.rel_name)
        self.rel.load(model)
        if self.col is None:
            col_expr = self.rel.model.primary_key.distinct()
        elif isinstance(self.col, str):
            col_expr = model.get_expr(self.col).distinct()
        else:
            col_expr = self.col(model.rec)
        self.expr = self.func(text(str(col_expr)))
        if self.data_type is None:
            self.data_type = DataType.get(self.expr)
        self.filter_clause = self.get_filter_clause()
        self.from_items[model.name] = self.rel.get_from_items()


class Relationship(BaseField):
    """
    Represents a relationship field.

    >>> from jsonapi.model import ONE_TO_MANY
    >>> from jsonapi.tests.db import articles_t
    >>>
    >>> Relationship('articles', 'ArticleModel', ONE_TO_MANY,
    >>>              articles_t.c.author_id)
    """

    def __init__(self, name, model_name, cardinality, *refs, **kwargs):
        """
        :param str name: relationship name
        :param str model_name: related model name
        :param Cardinality cardinality: relationship cardinality
        :param refs: a variable length list of foreign key columns
        """
        super().__init__(name)
        self.cardinality = cardinality
        self.model_name = model_name
        self.check_refs(refs)
        self.refs = refs
        self.model = None
        self.nested = None
        self.parent = None
        self.where = kwargs.get('where', None)

    def check_refs(self, refs):
        for ref in refs:
            if not isinstance(ref, Column):
                raise Error('invalid "ref" value: {!r}'.format(ref))

        if self.cardinality == Cardinality.MANY_TO_MANY and len(refs) != 2:
            raise Error('two "ref" columns required: {}'.format(', '.join(r.name) for r in refs))

        if self.cardinality in (Cardinality.MANY_TO_ONE, Cardinality.ONE_TO_MANY) and len(refs) != 1:
            raise Error('one "ref" column required: {}'.format(', '.join(r.name) for r in refs))

        if self.cardinality == Cardinality.ONE_TO_ONE and len(refs) > 1:
            raise Error('too many "ref" columns: {}'.format(', '.join(r.name) for r in refs))

    def get_from_items(self, related=False):

        if self.model is None and self.parent is None:
            raise Error('relationship: {!r} not loaded')

        if self.where is not None and not is_clause(self.where):
            raise ModelError('{!r} | invalid "where" clause'.format(self), self.model)

        from_items = list()

        if self.cardinality == Cardinality.ONE_TO_ONE:
            if self.refs:
                from_items.append(FromItem(
                    self.refs[0].table,
                    onclause=get_primary_key(self.refs[0].table) == self.parent.primary_key,
                    left=True))
            from_items.append(FromItem(
                self.model.primary_key.table,
                onclause=self.model.primary_key == (self.refs[0] if self.refs else self.parent.primary_key),
                left=True))

        elif self.cardinality == Cardinality.MANY_TO_ONE:
            ref = self.parent.from_clause.get_column(self.refs[0])
            if ref is not None:
                from_items.append(FromItem(
                    self.parent.primary_key.table if related else self.model.primary_key.table,
                    onclause=self.model.primary_key == ref,
                    left=True))
            else:
                from_items.append(FromItem(
                    self.refs[0].table,
                    onclause=self.model.primary_key == self.refs[0],
                    left=True))
                from_items.append(FromItem(
                    self.parent.primary_key.table,
                    onclause=get_primary_key(self.refs[0].table) == self.parent.primary_key,
                    left=True))

        elif self.cardinality == Cardinality.ONE_TO_MANY:
            ref = self.model.from_clause.get_column(self.refs[0])
            if ref is not None:
                from_items.append(FromItem(
                    self.model.primary_key.table,
                    onclause=self.parent.primary_key == ref,
                    left=True))
            else:
                from_items.append(FromItem(
                    self.refs[0].table,
                    onclause=self.model.primary_key == get_primary_key(self.refs[0]),
                    left=True))
                from_items.append(FromItem(
                    self.parent.primary_key.table,
                    onclause=self.refs[0] == self.parent.primary_key,
                    left=True))

        else:
            if related:
                onclause = self.model.primary_key == self.refs[1]
                if self.where is not None:
                    onclause = and_(onclause, self.where)
                from_items.append(FromItem(self.refs[1].table, onclause=onclause, left=True))
                from_items.append(FromItem(
                    self.parent.primary_key.table,
                    onclause=self.parent.primary_key == self.refs[0],
                    left=True))
            else:
                onclause = self.refs[0] == self.parent.primary_key
                if self.where is not None:
                    onclause = and_(onclause, self.where)
                from_items.append(FromItem(self.refs[0].table, onclause=onclause, left=True))
                from_items.append(FromItem(
                    self.model.primary_key.table,
                    onclause=self.model.primary_key == self.refs[1],
                    left=True))

        return tuple(from_items)

    @property
    def parent_col(self):
        if self.cardinality == Cardinality.ONE_TO_ONE:
            return self.model.primary_key
        if self.cardinality == Cardinality.ONE_TO_MANY:
            return self.model.from_clause.get_column(self.refs[0])
        return self.parent.primary_key

    def load(self, parent):
        if not self.model:
            self.parent = parent
            name = '_{}_{}'.format(parent.name, self.name)
            if name in model_registry:
                cls = model_registry[name]
            else:
                base = model_registry[self.model_name]
                cls = type(name,
                           (base,),
                           {'type_': base.get_type(),
                            'from_': base.get_from_aliases(self.name)})
            self.model = cls()
            self.filter_clause = self.get_filter_clause()
