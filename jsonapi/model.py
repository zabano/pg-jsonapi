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
from jsonapi.exc import APIError
from jsonapi.exc import NotFound
from jsonapi.fields import Aggregate
from jsonapi.fields import Derived
from jsonapi.fields import Field
from jsonapi.fields import Relationship
from jsonapi.registry import model_registry
from jsonapi.registry import schema_registry
from jsonapi.util import RequestArguments

MIME_TYPE = 'application/vnd.api+json'


def get_error_object(e):
    if isinstance(e, APIError):
        return dict(data=dict(errors=[dict(
            title=str(e),
            status=e.status if hasattr(e, 'status') else 500)]))
    raise e


class JSONSchema(marshmallow.Schema):

    @marshmallow.post_dump(pass_many=False, pass_original=True)
    def wrap(self, data, orig, many):

        if len(data) == 0:
            return

        resource = dict(id=data['id'], type=orig['type'], attributes=dict())
        for name, field in self.declared_fields.items():
            if name not in ('id', 'type') and not isinstance(field, marshmallow.fields.Nested):
                resource['attributes'][camelize(name, False)] = data[name]
            elif isinstance(field, marshmallow.fields.Nested) and not field.load_only:
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

        self.args = None
        self.query = Query(self)
        self.included = defaultdict(dict)
        self.errors = list()
        self.meta = dict()

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

    @property
    def attributes(self):
        """
        A dictionary of attribute fields keyed by name.
        """
        return {field.name: field for field in self.schema_fields if
                not isinstance(field, Relationship)}

    def get_relationship(self, name):
        for field in self.fields:
            if isinstance(field, Relationship) and name == field.name:
                return field
        return ModelError('relationship does not exist: "{}"'.format(name), self)

    def parse_arguments(self, args):
        self.args = RequestArguments(args)

    def init_schema(self, args=None):

        if args is not None:
            self.args = args

        self.schema_fields = [Field('id', self.primary_key, String)]
        columns = {col.name: col for col in self.query.columns}
        for field in self.fields:

            name = field if isinstance(field, str) else field.name
            in_include = self.args.in_include(name)
            fieldset_defined = self.args.fieldset_defined(self.type_)
            in_fieldset = self.args.in_fieldset(self.type_, name)
            in_sort = self.args.in_sort(name)

            if isinstance(field, str):
                if name not in columns:
                    raise ModelError('field: "{}" not found'.format(name), self)
                if not fieldset_defined or in_fieldset:
                    field = Field(field, columns[field])
                    field.exclude = in_sort and fieldset_defined and not in_fieldset
                    self.schema_fields.append(field)

            elif isinstance(field, (Field, Derived)):
                if not fieldset_defined or in_fieldset:
                    field.exclude = in_sort and fieldset_defined and not in_fieldset
                    self.schema_fields.append(field)

            elif isinstance(field, Aggregate):
                if in_fieldset:
                    field.exclude = in_sort and fieldset_defined and not in_fieldset
                    self.schema_fields.append(field)

            elif isinstance(field, Relationship):
                if in_include:
                    rel_args = copy(self.args)
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
                      {field.name: field() for field in self.schema_fields if not field.exclude})
        schema_registry[schema.__name__] = schema
        self.schema = schema()
        self.schema.context['root'] = self

    def response(self, data):
        response = dict(data=self.schema.dump(data, many=isinstance(data, list)))
        if len(self.included) > 0:
            response['included'] = reduce(lambda a, b: a + [rec for rec in b.values()],
                                          self.included.values(), list())
        if len(self.meta) > 0:
            response['meta'] = self.meta
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
        self.parse_arguments(args)
        self.init_schema()
        query = self.query.get(object_id)
        result = await pg.fetchrow(query)
        if result is None:
            raise NotFound(object_id, self)
        rec = dict(result)
        await self.fetch_included([rec])
        return self.response(rec)

    async def get_collection(self, args, filter_by=None):
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
        :param Filter filter_by: a Filter object for row filtering
        :return: a dictionary representing a JSON API response
        """
        self.parse_arguments(args)
        self.init_schema()
        query = self.query.all(filter_by=filter_by, paginate=True)
        recs = [dict(rec) for rec in await pg.fetch(query)]

        if self.args.limit is not None:
            self.meta['total'] = await pg.fetchval(self.query.all(
                filter_by=filter_by, paginate=False, count=True))
            if filter_by is not None:
                self.meta['totalFiltered'] = await pg.fetchval(self.query.all(
                    filter_by=filter_by, paginate=False, count=True))

        if filter_by is not None:
            self.meta['total'] = await pg.fetchval(self.query.all(
                paginate=False, count=True))

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

        result = await pg.fetchrow(self.query.get(object_id))
        if result is None:
            raise NotFound(object_id, self)

        rel = self.get_relationship(relationship_name)
        rel.model.parse_arguments(args)
        rel.model.init_schema()
        query = rel.model.query.related(object_id, rel)
        if rel.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
            result = await pg.fetchrow(query)
            data = dict(result) if result is not None else None
        else:
            data = [dict(rec) for rec in await pg.fetch(query)]
        await rel.model.fetch_included(data)
        return rel.model.response(data)

    def __repr__(self):
        return '<Model({})>'.format(self.name)
