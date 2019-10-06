from collections import defaultdict
from copy import copy
from functools import reduce
from itertools import islice

import marshmallow as ma
from asyncpgsa import pg
from inflection import camelize, dasherize, underscore

from jsonapi.args import RequestArguments
from jsonapi.datatypes import Integer, String
from jsonapi.db.filter import Filter
from jsonapi.db.query import Query
from jsonapi.db.table import Cardinality, FromClause, is_from_item
from jsonapi.db.util import get_primary_key
from jsonapi.exc import APIError, Error, Forbidden, ModelError, NotFound
from jsonapi.fields import Aggregate, BaseField, Derived, Field, Relationship
from jsonapi.registry import model_registry, schema_registry

MIME_TYPE = 'application/vnd.api+json'


def get_error_object(e):
    if isinstance(e, APIError):
        return dict(errors=[dict(
            title=str(e),
            status=e.status if hasattr(e, 'status') else 500)])
    raise e


class JSONSchema(ma.Schema):

    @ma.post_dump(pass_many=False, pass_original=True)
    def wrap(self, data, orig, many):

        if len(data) == 0:
            return

        resource = dict(id=data['id'], type=orig['type'], attributes=dict())

        if '_ts_rank' in orig:
            resource['meta'] = dict(rank=orig['_ts_rank'])

        for name, field in self.declared_fields.items():
            if name not in ('id', 'type') and not isinstance(field, ma.fields.Nested):
                resource['attributes'][camelize(name, False)] = data[name]
            elif isinstance(field, ma.fields.Nested) and not field.load_only:
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

    access = None
    """
    Resource access protection.
    """

    search = None
    """
    A full-text index table.
    """

    ################################################################################################
    # initialization
    ################################################################################################

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        model_registry[cls.__name__] = cls

    def __init__(self):

        self.type_ = self.get_type()
        self.from_clause = self.get_from_items()

        self.schema = None
        self.args = None

        self.fields = self.get_fields()
        self.query = Query(self)

        self.included = defaultdict(dict)
        self.meta = dict()

    def get_type(self):
        if self.type_ is None:
            return dasherize(underscore(self.name)).replace('model', '').strip('-')
        if not isinstance(self.type_, str):
            raise ModelError('attribute: "type_" must be a string', self)

    def get_from_items(self):
        if self.from_ is None:
            raise ModelError('attribute: "from_" is not set', self)
        try:
            for from_item in self.from_:
                if not is_from_item(from_item):
                    raise ModelError('invalid from item: {!r}'.format(from_item), self)
            return FromClause(*self.from_)
        except TypeError:
            if not is_from_item(self.from_):
                raise ModelError('invalid from item: {!r}'.format(self.from_), self)
            return FromClause(self.from_)

    def get_fields(self):
        fields = dict()
        if hasattr(self, 'fields'):
            if isinstance(self.fields, str):
                field = self.get_field(self.fields)
                fields[field.name] = field
            else:
                try:
                    iter(self.fields)
                except TypeError:
                    field = self.get_field(self.fields)
                    fields[field.name] = field
                else:
                    for field_spec in self.fields:
                        field = self.get_field(field_spec)
                        fields[field.name] = field

        if 'id' in fields.keys():
            raise APIError('illegal field name: "id"', self)
        elif 'type' in fields.keys():
            raise APIError('illegal field name: "type"', self)

        fields['id'] = Field('id', self.primary_key, String)
        return fields

    def get_field(self, field_spec):
        if isinstance(field_spec, str):
            expr = self.get_db_column(field_spec)
            if expr is None:
                raise ModelError('db column: "{}" '
                                 'not found'.format(field_spec), self)
            return Field(field_spec, expr)
        elif isinstance(field_spec, BaseField):
            return field_spec
        else:
            raise ModelError('invalid field: {!r}'.format(field_spec), self)

    def get_db_column(self, name):
        for col in self.from_clause().columns:
            if col.name == name:
                return col

    def attribute(self, name):
        if name in self.fields.keys() and not isinstance(self.fields[name], Relationship):
            return self.fields[name]
        raise ModelError('attribute does not exist: "{}"'.format(name), self)

    def relationship(self, name):
        if name in self.fields.keys() and isinstance(self.fields[name], Relationship):
            return self.fields[name]
        return ModelError('relationship does not exist: "{}"'.format(name), self)

    ################################################################################################
    # properties
    ################################################################################################

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
        return {name: field for name, field in self.fields.items()
                if isinstance(field, Relationship) and not field.exclude}

    @property
    def attributes(self):
        """
        A dictionary of attribute fields keyed by name.
        """
        return {name: field for name, field in self.fields.items()
                if not isinstance(field, Relationship)
                and not field.exclude
                and field.expr is not None}

    ################################################################################################
    # core functionality
    ################################################################################################

    def parse_arguments(self, args):
        self.args = RequestArguments(args)

    def init_schema(self, args=None):

        if args is not None:
            self.args = args

        for name, field in self.fields.items():

            in_include = self.args.in_include(name)
            fieldset_defined = self.args.fieldset_defined(self.type_)
            in_fieldset = self.args.in_fieldset(self.type_, name)
            in_sort = self.args.in_sort(name)
            in_filter = self.args.in_filter(name)

            if isinstance(field, (Field, Derived)):
                field.exclude = fieldset_defined and not in_fieldset

            elif isinstance(field, Aggregate):
                field.exclude = not in_fieldset
                if in_fieldset or in_sort or in_filter:
                    field.load(self)

            elif isinstance(field, Relationship):
                field.exclude = not in_include
                if in_include:
                    rel_args = copy(self.args)
                    rel_args.include = rel_args.include[field.name]
                    field.model.init_schema(rel_args)

            else:
                raise ModelError('unsupported field: {!r}'.format(field), self)

        schema = type('{}Schema'.format(self.name),
                      (JSONSchema,),
                      {name: field.get_ma_field() for name, field in self.fields.items()
                       if not field.exclude})
        schema_registry[schema.__name__] = schema
        self.schema = schema()
        self.schema.context['root'] = self

    def response(self, data):
        response = dict(data=self.schema.dump(data, many=isinstance(data, list)))
        if len(self.included) > 0:
            response['included'] = reduce(lambda a, b: a + [rec for rec in b.values()],
                                          self.included.values(), list())
            self.included.clear()
        if len(self.meta) > 0:
            response['meta'] = dict(self.meta)
            self.meta = dict()
        return response

    async def paginate(self, filter_by):
        if self.args.limit is not None:
            self.meta['total'] = await pg.fetchval(self.query.all(
                filter_by=filter_by, paginate=False, count=True))
            if filter_by:
                self.meta['totalFiltered'] = await pg.fetchval(self.query.all(
                    filter_by=filter_by, paginate=False, count=True))

        if filter_by:
            self.meta['total'] = await pg.fetchval(self.query.all(
                paginate=False, count=True))

    def get_filter(self, args):
        filter_by = Filter()
        for key, arg in self.args.filter.items():
            try:
                attr = self.attribute(arg['name'])
            except Error as e:
                try:
                    custom_filter = getattr(self, 'filter_{}'.format(arg['name']))
                except AttributeError:
                    raise APIError('filter:{} | {}'.format(arg['name'], e), self)
                except Error as e:
                    raise ModelError(e, self)
                else:
                    filter_by.add_custom(arg['name'], custom_filter(args[key]))
            else:
                try:
                    filter_by.add(attr, arg['op'], args[key])
                except Error as e:
                    raise APIError('filter:{} | {}'.format(attr.name, e), self)
        return filter_by

    async def fetch_included(self, data):

        if not isinstance(data, list):
            data = list() if data is None else [data]

        for rec in data:
            rec['type'] = self.type_

        for rel in self.relationships.values():
            result = list()
            for query in rel.model.query.included(rel, [rec['id'] for rec in data]):
                result.extend(await pg.fetch(query))

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

    ################################################################################################
    # public interface
    ################################################################################################

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

        if not await pg.fetchval(self.query.exists(object_id)):
            raise NotFound(object_id, self)

        query = self.query.get(object_id)
        result = await pg.fetchrow(query)
        if result is None:
            raise Forbidden(object_id, self)
        rec = dict(result)
        await self.fetch_included([rec])
        return self.response(rec)

    async def get_collection(self, args, search=None):
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
        :param str search: an optional search term
        :return: a dictionary representing a JSON API response
        """
        self.parse_arguments(args)
        self.init_schema()
        filter_by = self.get_filter(args)
        query = self.query.all(filter_by=filter_by, paginate=True, search=search)
        recs = [dict(rec) for rec in await pg.fetch(query)]
        await self.paginate(filter_by)
        await self.fetch_included(recs)
        return self.response(recs)

    async def get_related(self, args, object_id, relationship_name, search=None):
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
        :param str search: an optional search term
        :return: a dictionary representing a JSON API response
        """

        if not await pg.fetchval(self.query.exists(object_id)):
            raise NotFound(object_id, self)

        result = await pg.fetchrow(self.query.get(object_id))
        if result is None:
            raise Forbidden(object_id, self)

        rel = self.relationship(relationship_name)
        rel.model.parse_arguments(args)
        rel.model.init_schema()
        filter_by = rel.model.get_filter(args)
        query = rel.model.query.related(
            object_id, rel, filter_by=filter_by, paginate=True, search=search)
        if rel.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
            result = await pg.fetchrow(query)
            data = dict(result) if result is not None else None
        else:
            data = [dict(rec) for rec in await pg.fetch(query)]
            await rel.model.paginate(filter_by)
        await rel.model.fetch_included(data)
        return rel.model.response(data)

    def __repr__(self):
        return '<Model({})>'.format(self.name)


class MixedModel:
    """
    A mixed model defines a heterogeneous set of JSON API resources.
    """

    models = None
    """
    A set of resource models
    """

    def __init__(self):
        models = set()
        for model in self.models:
            if isinstance(model, Model):
                models.add(model)
            elif issubclass(model, Model):
                models.add(model())
            else:
                raise ModelError('invalid model: {:!r}'.format(model), self)
        self.models = models

    @property
    def name(self):
        return self.__class__.__name__

    async def search(self, args, term):

        args = RequestArguments(args)

        data = list()
        total = 0
        for model in self.models:
            async with pg.query(model.query.search(term)) as cursor:
                async for row in cursor:
                    data.append(dict(type=model.type_, id=str(row['id']), rank=row['_ts_rank']))
                    total += 1
        data = sorted(data, key=lambda x: x['rank'], reverse=True)

        sliced_data = defaultdict(dict)
        for rec in islice(data, args.offset, args.offset + args.limit):
            sliced_data[rec['type']][rec['id']] = rec['rank']

        result = list()
        for model in self.models:
            id_list = list(object_id for object_id in sliced_data[model.type_].keys())
            if len(id_list) > 0:
                model.parse_arguments({})
                model.init_schema()
                result.extend(model.schema.dump(
                    [{'type': model.type_, **rec} for rec in await pg.fetch(
                        model.query.all(filter_by=model.primary_key.in_(
                            [int(object_id) if isinstance(model.primary_key.type,
                                                          Integer.sa_types)
                             else object_id for object_id in id_list]
                        )))], many=True))

        # todo:: add support for "fields" and "include" request parameters

        return dict(
            data=sorted(result, key=lambda x: sliced_data[x['type']][x['id']], reverse=True),
            meta=dict(total=total))
