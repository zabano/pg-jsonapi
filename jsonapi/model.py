import enum
from copy import copy
from collections import defaultdict
from functools import reduce

import marshmallow
import marshmallow.class_registry
import sqlalchemy as sa
from asyncpgsa import pg
from inflection import camelize

from jsonapi.db import Cardinality
from jsonapi.db import FromClause
from jsonapi.db import FromItem
from jsonapi.db import Query
from jsonapi.db import get_primary_key
from jsonapi.exc import Error
from jsonapi.exc import ModelError
from jsonapi.util import ArgumentParser

MIME_TYPE = 'application/vnd.api+json'

_registry = {}
"""
Model Registry.

A dictionary of Model classes, keyed by name.
Example: {'UserModel': UserModel, 'ArticleModel': ArticleMode}.
"""


class FieldType(enum.Enum):
    """
    Field data types.
    """
    Bool = marshmallow.fields.Bool()
    Integer = marshmallow.fields.Integer()
    Float = marshmallow.fields.Float()
    String = marshmallow.fields.String()
    Date = marshmallow.fields.Date()
    DateTime = marshmallow.fields.DateTime('%Y-%m-%dT%H:%M:%SZ')
    Time = marshmallow.fields.Time()


Bool = FieldType.Bool
Integer = FieldType.Integer
Float = FieldType.Float
String = FieldType.String
Date = FieldType.Date
DateTime = FieldType.DateTime
Time = FieldType.Time


class Field:
    """
    Simple field type.

    Use this field type to pass a custom sql expression or force a type

    >>> from jsonapi.tests.db import users_t, user_names_t
    >>> Field('emil_address', users_t.c.email)
    >>> Field('name', user_names_t.c.first + ' ' + user_names_t.c.last)
    >>> Field('created_on', type_=Date)

    .. note::

        This class also serve as a base for all other field types.
    """

    def __init__(self, name, expr=None, type_=None):
        """
        Initialize a model field.

        :param str name: a unique field name
        :param mixed expr: an sql expression
        :param FieldType type_: one of the supported field types
        """

        if type_ is not None and not isinstance(type_, FieldType):
            raise Error('invalid attribute type provided: "{}"'.format(type_))

        self.name = name
        self.expr = expr
        self.type_ = self._get_type(expr) if type_ is None else type_.value

    @staticmethod
    def _get_type(expr):
        if expr is not None:
            if hasattr(expr, 'type'):
                if isinstance(expr.type, sa.Boolean):
                    return Bool.value
                if isinstance(expr.type, (sa.Integer, sa.SmallInteger, sa.BigInteger)):
                    return Integer.value
                if isinstance(expr.type, (sa.Float, sa.Numeric)):
                    return Float.value
                if isinstance(expr.type, sa.Date):
                    return Date.value
                if isinstance(expr.type, sa.DateTime):
                    return DateTime.value
                if isinstance(expr.type, sa.Time):
                    return Time.value
            return String.value

    def __repr__(self):
        return '<Field({})>'.format(self.name)


class Relationship(Field):
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

        if cardinality not in Cardinality:
            raise Error('invalid cardinality value: {}'.format(cardinality))

        super().__init__(name)
        self.cardinality = cardinality

        self._model_name = model_name
        self._fkey_name = fkey_name

        self._model = None
        self._fkey = None

    @property
    def model(self):
        if self._model is None:
            self._model = _registry[self._model_name]()
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

    def __repr__(self):
        return '<Relationship({})>'.format(self.name)


class Aggregate(Field):
    """
    Represents an aggregate field (e.g. count, max, etc.)

    To define an aggregate field, an aggregate expression must be provided,
    along with one or more from items to join to the model's from clause.
    """

    def __init__(self, name, expr, from_items=None, type_=Integer):
        """
        :param str name: relationship name
        :param expr: SQLAlchemy expression representing an aggregate column
        :param mixed from_items: additional from items
        :param FieldType type_: one of the supported field types
        """
        super().__init__(name, expr, type_)

        if from_items is None:
            self._from_items = tuple()
        elif isinstance(from_items, FromItem):
            self._from_items = from_items,
        elif isinstance(from_items, (list, tuple)):
            for from_item in self._from_items:
                if not isinstance(from_item, FromItem):
                    raise Error('invalid From item passed to: {!r}'.format(self))
            self._from_items = tuple(from_items)
        else:
            raise Error('invalid from_items value: {} passed to: {!r}'.format(from_items, self))

    def __repr__(self):
        return '<Aggregate({})>'.format(self.name)


class Derived(Field):
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
        self.type_ = marshmallow.fields.Function(expr)

    def __repr__(self):
        return '<Derived({})>'.format(self.name)


class JSONSchema(marshmallow.Schema):

    @marshmallow.post_dump(pass_many=False, pass_original=True)
    def wrap(self, data, orig, many):
        resource = dict(id=data['id'], type=orig['type'], attributes=dict())
        for name, field in self.declared_fields.items():
            if name not in ('id', 'type') and not isinstance(field, marshmallow.fields.Nested):
                resource['attributes'][camelize(name, False)] = data[name]
            elif isinstance(field, marshmallow.fields.Nested):
                if 'relationships' not in resource:
                    resource['relationships'] = dict()
                included = self.context['root'].included
                if isinstance(data[name], list):
                    resource['relationships'][name] = [
                        dict(id=rec['id'], type=rec['type']) for rec in data[name]]
                    if len(data[name]) > 0:
                        for rec in data[name]:
                            included[rec['type']][rec['id']] = rec
                else:
                    if data[name] is None:
                        resource['relationships'][name] = None
                    else:
                        resource['relationships'][name] = dict(
                            id=data[name]['id'], type=orig[name]['type'])
                        included[orig[name]['type']][data[name]['id']] = data[name]
        return resource


class Model:
    """
    A model defines a JSON API resource.
    """

    type_ = None
    """
    Unique resource type (str)
    """

    from_ = None
    """
    A variable length list of tables, table aliases, or :class:`jsonapi.db.FromItem` s.
    """

    fields = None
    """
    A variable length list of fields or field names.
    """

    search = None
    """
    A full-text index table.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _registry[cls.__name__] = cls

    def __init__(self):

        if self.type_ is None:
            raise ModelError('attribute: "type_" is not set', self)
        if not isinstance(self.type_, str):
            raise ModelError('attribute: "type_" must be a string', self)

        if self.from_ is None:
            raise ModelError('attribute: "from_" is not set', self)
        self.from_clause = FromClause(
            *(self.from_ if isinstance(self.from_, (list, tuple)) else (self.from_,)))

        if self.fields is None:
            self.fields = tuple()
        elif isinstance(self.fields, (list, tuple)):
            self.fields = tuple(self.fields)
        else:
            self.fields = (self.fields,)

        self.schema = None
        self.schema_fields = list()

        self.query = Query(self)
        self.included = defaultdict(dict)

    def _is_attribute_excluded(self, args, name):
        return self.type_ in args.fields.keys() and name not in args.fields[self.type_]

    @property
    def name(self):
        """
        Unique model name.
        """
        return self.__class__.__name__

    @property
    def primary_key(self):
        """
        A database column representing the Model's primary key.
        """
        return get_primary_key(self.from_clause[0].table)

    @property
    def relationships(self):
        """
        A dictionary of relationship fields keyed by name.
        """
        return {field.name: field for field in self.schema_fields if
                isinstance(field, Relationship)}

    def init_schema(self, args):

        self.schema_fields = [Field('id', self.primary_key, String)]
        columns = {col.name: col for col in self.query.columns}
        for field in self.fields:

            if isinstance(field, str):
                if field not in columns:
                    raise ModelError('field: "{}" not found'.format(field), self)
                if not self._is_attribute_excluded(args, field):
                    self.schema_fields.append(Field(field, columns[field]))

            elif type(field) in (Field, Derived):
                if not self._is_attribute_excluded(args, field.name):
                    self.schema_fields.append(field)

            elif isinstance(field, Relationship):
                if field.name in args.include.keys():
                    rel_args = copy(args)
                    rel_args.include = rel_args.include[field.name]
                    field.model.init_schema(rel_args)

                    field.type_ = marshmallow.fields.Nested(
                        marshmallow.class_registry.get_class('{}Schema'.format(field.model.name))(),
                        many=field.cardinality in (Cardinality.ONE_TO_MANY,
                                                   Cardinality.MANY_TO_MANY))
                    self.schema_fields.append(field)

            # else:
            #     raise ModelError('unsupported field: {!r}'.format(field), self)

        self.schema = type('{}Schema'.format(self.name),
                           (JSONSchema,),
                           {field.name: field.type_ for field in self.schema_fields})()
        self.schema.context['root'] = self

    def response(self, data):
        response = dict(data=self.schema.dump(data, many=isinstance(data, list)))
        if len(self.included) > 0:
            response['included'] = reduce(lambda a, b: a + [rec for rec in b.values()],
                                          self.included.values(), list())
        return response

    async def fetch_included(self, data):

        if not isinstance(data, list):
            data = list() if data is None else [data]

        for rec in data:
            rec['type'] = self.type_

        for rel in self.relationships.values():
            result = await pg.fetch(rel.model.query.included(rel, [rec['id'] for rec in data]))

            recs_by_parent_id = defaultdict(list)
            for rec in result:
                rec = dict(rec)
                parent_id = rec.pop('parent_id')
                recs_by_parent_id[parent_id].append(rec)

            for parent in data:
                parent_id = parent['id']
                if rel.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
                    parent[rel.name] = recs_by_parent_id[parent_id][0] \
                        if parent_id in recs_by_parent_id else None
                else:
                    parent[rel.name] = recs_by_parent_id[parent_id] \
                        if parent_id in recs_by_parent_id else list()

            await rel.model.fetch_included(
                reduce(lambda a, b: a + b if isinstance(b, list) else a + [b],
                       [rec[rel.name] for rec in data if rec[rel.name] is not None],
                       list()))

    async def get_object(self, args, object_id):
        """
        Fetch a resource object.

        >>> from jsonapi.tests.model import UserModel
        >>> await UserModel().get_object({
        >>>     'include': 'articles.comments.author,articles.keywords',
        >>>     'fields[article]': 'title,body',
        >>>     'fields[comments]': 'body',
        >>>     'fields[user]': 'name'
        >>> }, 1)

        :param dict args: a dictionary representing the request query string
        :param int or str object_id: the resource object id
        :return: a dictionary representing a JSON API response
        """
        self.init_schema(ArgumentParser(args))
        rec = dict(await pg.fetchrow(self.query.get(object_id)))
        await self.fetch_included([rec])
        return self.response(rec)

    async def get_collection(self, args):
        """
        Fetch a collection of resources.

        >>> from jsonapi.tests.model import UserModel
        >>> await UserModel().get_collection({
        >>>     'include': 'articles.comments.author,articles.keywords',
        >>>     'fields[article]': 'title,body',
        >>>     'fields[comments]': 'body',
        >>>     'fields[user]': 'name'
        >>> })

        :param dict args: a dictionary representing the request query string
        :return: a dictionary representing a JSON API response
        """
        self.init_schema(ArgumentParser(args))
        recs = [dict(rec) for rec in await pg.fetch(self.query.all())]
        await self.fetch_included(recs)
        return self.response(recs)

    async def get_related(self, args, object_id, relationship_name):
        """
        Fetch a collection of related resources.

        >>> from jsonapi.tests.model import ArticleModel
        >>> await ArticleModel().get_related({
        >>>     'include': 'articles.comments,articles.keywords',
        >>>     'fields[article]': 'title,body',
        >>>     'fields[comments]': 'body'
        >>> }, 1, 'author')

        :param dict args: a dictionary representing the request query string
        :param object_id: the resource object id
        :param relationship_name: relationship name
        :return: a dictionary representing a JSON API response
        """
        self.init_schema(ArgumentParser(dict(include=relationship_name)))
        rel = self.relationships[relationship_name]
        query = rel.model.query.related(object_id, rel)
        recs = [dict(rec) for rec in await pg.fetch(query)] if rel.cardinality in (
            Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY) else dict(await pg.fetchrow(query))
        rel.model.init_schema(ArgumentParser(args))
        await rel.model.fetch_included(recs)
        return rel.model.response(recs)

    def __repr__(self):
        return '<Model({})>'.format(self.name)
