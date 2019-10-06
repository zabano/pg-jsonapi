import marshmallow as ma

from jsonapi.datatypes import DataType, Date, Integer
from jsonapi.db.table import Cardinality, FromItem
from jsonapi.exc import APIError, Error, ModelError
from jsonapi.registry import alias_registry, model_registry, schema_registry


class BaseField:
    """ The base class for all field types """

    def __init__(self, name, expr=None, data_type=None):

        if data_type is not None and not isinstance(data_type, DataType):
            raise Error('invalid data type provided: "{}"'.format(data_type))

        self.name = name
        self.expr = expr
        self.data_type = DataType.get(expr) if data_type is None else data_type
        self.exclude = False

        self.filter_clause = self.get_filter_clause()

    def get_filter_clause(self):
        data_type = Integer if self.name == 'id' else self.data_type
        if data_type is not None:
            return data_type.filter_clause

    def is_aggregate(self):
        return isinstance(self, Aggregate)

    def get_ma_field(self):
        if isinstance(self, Relationship):
            return ma.fields.Nested(
                schema_registry['{}Schema'.format(self.model.name)](),
                many=self.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY))
        if isinstance(self, Derived):
            return ma.fields.Function(self.func)
        if issubclass(self.data_type.ma_type, ma.fields.Date):
            return self.data_type.ma_type(format=DataType.FORMAT_DATE)
        if issubclass(self.data_type.ma_type, ma.fields.DateTime):
            return self.data_type.ma_type(format=DataType.FORMAT_DATETIME)
        return self.data_type.ma_type()

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.name)


class Field(BaseField):
    """
    Basic field type, which maps to a database table column or expression.

    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> from jsonapi.datatypes import Date
    >>> Field('emil_address', users_t.c.email)
    >>> Field('name', user_names_t.c.first + ' ' + user_names_t.c.last)
    >>> Field('created_on', data_type=Date)
    """


class Aggregate(BaseField):
    """
    Represents an aggregate field (e.g. count, max, etc.)

    To define an aggregate field, an aggregate expression must be provided,
    along with one or more from items to add to the model's from clause.
    """

    def __init__(self, name, rel_name, func, data_type=None):
        """
        :param str name: field name
        :param rel_name: relationship name
        :param func: SQLAlchemy aggregate function (ex. sa.func.count)
        :param DataType data_type: one of the supported data types (optional)
        """
        super().__init__(name, expr=None, data_type=data_type if data_type is not None else Integer)
        self.func = func
        self.rel_name = rel_name
        self.rel = None
        self.from_items = tuple()

    def load(self, model):
        self.rel = model.relationship(self.rel_name)
        pkey = self.rel.model.primary_key
        fkey = self.rel.fkey
        alias_name = '{}_alias_for_{}'.format(self.rel.name, self.name)
        if alias_name in alias_registry:
            alias = alias_registry[alias_name]
        else:
            alias = pkey.table.alias()
        alias_pkey = getattr(alias.c, pkey.name)
        self.expr = self.func(alias_pkey.distinct())
        self.filter_clause = self.get_filter_clause()
        if self.rel.cardinality == Cardinality.MANY_TO_MANY:
            self.from_items = FromItem(alias, left=True), FromItem(fkey.parent.table, left=True)
        elif self.rel.cardinality == Cardinality.ONE_TO_MANY:
            self.from_items = FromItem(
                alias,
                onclause=fkey.column == getattr(alias.c, fkey.parent.name),
                left=True),
        else:
            raise APIError('aggregate field support only TO_MANY '
                           'relationships: "{}"'.format(self.name), model)


class Derived(BaseField):
    """
    Represents a derived field.

    >>> Derived('name', lambda rec: '{first} {last}.format(**rec)')
    """

    def __init__(self, name, expr):
        """
        :param str name: a unique field name
        :param lambda expr: a lambda function that accepts a single record as the first argument
        """
        super().__init__(name)
        self.func = expr


class Relationship(BaseField):
    """
    Represents a relationship field.

    >>> from jsonapi.db.table import ONE_TO_MANY
    >>> Relationship('articles', 'ArticleModel',
    >>>              ONE_TO_MANY, 'articles_author_id_fkey'))
    """

    def __init__(self, name, model_name, cardinality, fkey_name):
        """
        :param str name: relationship name
        :param str model_name: related model name
        :param Cardinality cardinality: relationship cardinality
        :param str fkey_name: SQLAlchemy foreign key name
        """
        super().__init__(name)
        self.cardinality = cardinality
        self.nested = None

        self._model_name = model_name
        self._fkey_name = fkey_name

        self._model = None
        self._fkey = None

    @property
    def model(self):
        if self._model is None:
            self._model = model_registry[self._model_name]()
        return self._model

    @property
    def fkey(self):
        if self._fkey is None:
            for table in self.model.from_clause[0].table.metadata.tables.values():
                for fk in table.foreign_keys:
                    if fk.name == self._fkey_name:
                        self._fkey = fk
                        return self._fkey
            raise ModelError('foreign key: "{}" not found'.format(self._fkey_name), self._model)
        return self._fkey
