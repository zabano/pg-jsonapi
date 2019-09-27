import sqlalchemy as sa
import marshmallow

from .exc import Error, ModelError
from .registry import model_registry
from .datatypes import DataType
from .datatypes import Bool
from .datatypes import Integer
from .datatypes import Float
from .datatypes import String
from .datatypes import Date
from .datatypes import DateTime
from .datatypes import Time


class BaseField:
    """ The base class for all field types """

    def __init__(self, name, expr=None, data_type=None):

        if data_type is not None and not isinstance(data_type, DataType):
            raise Error('invalid attribute type provided: "{}"'.format(data_type))

        self.name = name
        self.expr = expr
        self.data_type = self._get_data_type(expr).value if data_type is None else data_type.value
        self.exclude = False

    @staticmethod
    def _get_data_type(expr):
        if expr is not None:
            if hasattr(expr, 'type'):
                if isinstance(expr.type, sa.Boolean):
                    return Bool
                if isinstance(expr.type, (sa.Integer, sa.SmallInteger, sa.BigInteger)):
                    return Integer
                if isinstance(expr.type, (sa.Float, sa.Numeric)):
                    return Float
                if isinstance(expr.type, sa.Date):
                    return Date
                if isinstance(expr.type, sa.DateTime):
                    return DateTime
                if isinstance(expr.type, sa.Time):
                    return Time
        return String

    def __call__(self):

        if isinstance(self.data_type, (marshmallow.fields.Nested, marshmallow.fields.Function)):
            return self.data_type

        args = list()
        if issubclass(self.data_type, marshmallow.fields.DateTime):
            args = ['%Y-%m-%dT%H:%M:%SZ']
        return self.data_type(*args)

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.name)


class Field(BaseField):
    """
    Basic field type, which maps to a database table column or expression.

    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> from jsonapi import Date
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

    def __init__(self, name, rel_name, func, data_type=Integer):
        """
        :param str name: field name
        :param rel_name: relationship name
        :param func: SQLAlchemy aggregate function (ex. sa.func.count)
        :param DataType data_type: one of the supported data types (optional)
        """
        super().__init__(name, expr=None, data_type=data_type)
        self.func = func
        self.rel_name = rel_name
        self.rel = None
        self.from_items = None


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
        self.data_type = marshmallow.fields.Function(expr)


class Relationship(BaseField):
    """
    Represents a relationship field.

    >>> from jsonapi import ONE_TO_MANY
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
