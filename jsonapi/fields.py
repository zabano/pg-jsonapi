import marshmallow as ma
from sqlalchemy.sql import text

from jsonapi.datatypes import DataType, Date, Integer, String
from jsonapi.db.table import Cardinality, FromItem, get_foreign_key_pair
from jsonapi.exc import APIError, Error
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
    Basic field type, which maps to a database table column.

    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> from jsonapi.datatypes import Date
    >>> Field('emil_address')
    >>> Field('created_on', Date)
    """

    def load(self, model):
        if self.name == 'id':
            self.expr = model.primary_key
        else:
            self.expr = model.get_expr(self.name)
            if self.data_type is None:
                self.data_type = DataType.get(self.expr)
        self.filter_clause = self.get_filter_clause()


class Derived(BaseField):
    """
    Represents a derived field.

    >>> Derived('name', lambda c: c['first'] + ' ' + c['last'])
    >>> Derived('name', lambda c: c.first + ' ' + c.last)
    """

    def __init__(self, name, spec, data_type=None):
        """
        :param str name: a unique field name
        :param lambda spec: a lambda function that accepts a ColumnCollection
        :param DataType data_type: defaults to String
        """
        data_type = data_type if data_type is not None else String
        super().__init__(name, data_type=data_type)
        self.spec = spec

    def load(self, model):
        self.expr = self.spec(model.rec)
        self.filter_clause = self.get_filter_clause()


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
        :param func: SQLAlchemy aggregate function (ex. func.count)
        :param DataType data_type: one of the supported data types (optional)
        """
        data_type = data_type if data_type is not None else Integer
        super().__init__(name, data_type=data_type)
        self.func = func
        self.rel_name = rel_name
        self.rel = None
        self.from_items = dict()

    def load(self, model):
        self.rel = model.relationship(self.rel_name)
        self.rel.load(model)
        self.expr = self.func(text(str(self.rel.model.primary_key.distinct())))
        self.filter_clause = self.get_filter_clause()

        if self.rel.cardinality == Cardinality.MANY_TO_MANY:
            ref_model, _ = get_foreign_key_pair(self.rel.model, *self.rel.ref)
            self.from_items[model.name] = (
                FromItem(ref_model.table, left=True),
                FromItem(self.rel.model.primary_key.table, left=True))
        elif self.rel.cardinality == Cardinality.ONE_TO_MANY:
            from_item = FromItem(
                self.rel.model.primary_key.table,
                onclause=self.rel.parent.primary_key == self.rel.model.get_expr(
                    self.rel.ref),
                left=True)
            self.from_items[model.name] = (from_item,)
        else:
            raise APIError('error: "{}"'.format(self.name), model)


class Relationship(BaseField):
    """
    Represents a relationship field.

    >>> from jsonapi.model import ONE_TO_MANY
    >>> Relationship('articles', 'ArticleModel', ONE_TO_MANY, 'author_id'))
    """

    def __init__(self, name, model_name, cardinality, ref=None):
        """
        :param str name: relationship name
        :param str model_name: related model name
        :param Cardinality cardinality: relationship cardinality
        """
        super().__init__(name)
        self.cardinality = cardinality
        self.model_name = model_name
        self.ref = ref
        self.model = None
        self.nested = None
        self.parent = None

    def load(self, parent):
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
