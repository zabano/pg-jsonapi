from collections import defaultdict
from copy import copy
from functools import reduce

import marshmallow
from asyncpgsa import pg
from inflection import camelize

from jsonapi.datatypes import String
from jsonapi.db import Cardinality
from jsonapi.db import FromClause
from jsonapi.db import Query
from jsonapi.db import get_primary_key
from jsonapi.exc import ModelError
from jsonapi.fields import Aggregate
from jsonapi.fields import Derived
from jsonapi.fields import Field
from jsonapi.fields import Relationship
from jsonapi.registry import model_registry
from jsonapi.registry import schema_registry
from jsonapi.util import ArgumentParser

MIME_TYPE = 'application/vnd.api+json'


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
        model_registry[cls.__name__] = cls

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

    def _is_attribute_excluded(self, args, name, is_aggregate=False):
        if is_aggregate:
            return self.type_ not in args.fields.keys() or name not in args.fields[self.type_]
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

            elif isinstance(field, (Field, Derived, Aggregate)):
                if not self._is_attribute_excluded(
                        args, field.name, is_aggregate=isinstance(field, Aggregate)):
                    self.schema_fields.append(field)

            elif isinstance(field, Relationship):
                if field.name in args.include.keys():
                    rel_args = copy(args)
                    rel_args.include = rel_args.include[field.name]
                    field.model.init_schema(rel_args)
                    field.data_type = marshmallow.fields.Nested(
                        schema_registry['{}Schema'.format(field.model.name)](),
                        many=field.cardinality in (Cardinality.ONE_TO_MANY,
                                                   Cardinality.MANY_TO_MANY))
                    self.schema_fields.append(field)

            else:
                raise ModelError('unsupported field: {!r}'.format(field), self)

        schema = type('{}Schema'.format(self.name),
                      (JSONSchema,),
                      {field.name: field.data_type for field in self.schema_fields})
        schema_registry[schema.__name__] = schema
        self.schema = schema()
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
        query = self.query.get(object_id)
        rec = dict(await pg.fetchrow(query))
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
        query = self.query.all()
        recs = [dict(rec) for rec in await pg.fetch(query)]
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
        rel.model.init_schema(ArgumentParser(args))
        query = rel.model.query.related(object_id, rel)
        recs = [dict(rec) for rec in await pg.fetch(query)] if rel.cardinality in (
            Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY) else dict(await pg.fetchrow(query))
        await rel.model.fetch_included(recs)
        return rel.model.response(recs)

    def __repr__(self):
        return '<Model({})>'.format(self.name)
