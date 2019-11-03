import operator
from collections import defaultdict
from collections.abc import Sequence, Set
from copy import copy, deepcopy
from functools import reduce

import marshmallow as ma
from asyncpgsa import pg
from inflection import camelize, dasherize, underscore
from sqlalchemy.sql.expression import ColumnCollection, cast

from jsonapi.args import parse_arguments
from jsonapi.datatypes import String
from jsonapi.db.filter import FilterBy
from jsonapi.db.query import exists, search_query, select_many, select_merged, select_mixed, select_one, select_related
from jsonapi.db.table import Cardinality, FromClause, FromItem, OrderBy, get_primary_key, is_from_item
from jsonapi.exc import APIError, Error, Forbidden, ModelError, NotFound
from jsonapi.fields import Aggregate, BaseField, Field, Relationship
from jsonapi.log import log_query, logger
from jsonapi.registry import model_registry, schema_registry
from jsonapi.util import v

MIME_TYPE = 'application/vnd.api+json'
"""
The mime type to be used as the value of the Content-Type header
"""

SEARCH_PAGE_SIZE = 50
"""
The default value for the "page[size]" option when searching
"""

ONE_TO_ONE = Cardinality.ONE_TO_ONE
MANY_TO_ONE = Cardinality.MANY_TO_ONE
ONE_TO_MANY = Cardinality.ONE_TO_MANY
MANY_TO_MANY = Cardinality.MANY_TO_MANY


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
                    resource['relationships'][name] = [dict(id=rec['id'], type=rec['type']) for rec in data[name]]
                    if len(data[name]) > 0:
                        for rec in data[name]:
                            included[rec['type']][rec['id']] = rec
                else:
                    if data[name] is None:
                        resource['relationships'][name] = None
                    else:
                        resource['relationships'][name] = dict(id=data[name]['id'], type=orig[name]['type'])
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
    A sequence of fields or field names.
    """

    access = None
    """
    An SQL function providing object-level access protection.
    """

    user = None
    """
    A thread-safe object representing a logged-in user.
    """

    search = None
    """
    A full-text index table.
    """

    ####################################################################################################################
    # initialization
    ####################################################################################################################

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        model_registry[cls.__name__] = cls
        logger.info('created model: {!r}'.format(cls))

    def __init__(self):

        try:
            self.type_ = self.get_type()
            self.from_clause = self.get_from_clause()
            self.fields = self.get_fields()
        except Error as e:
            raise ModelError(e, self)

        self.schema = None
        self.included = defaultdict(dict)
        self.meta = dict()
        logger.info('initialized model: {!r}'.format(self))

    @classmethod
    def get_type(cls):
        if cls.type_ is None:
            type_ = dasherize(underscore(cls.__name__))
            return type_.replace('model', '').strip('-')
        if not isinstance(cls.type_, str):
            raise Error('"type_" must be a string')
        return cls.type_

    def get_from_clause(self):
        if self.from_ is None:
            raise ModelError('attribute: "from_" is not set', self)
        for from_item in v(self.from_):
            if not is_from_item(from_item):
                raise ModelError('invalid from item: {!r}'.format(from_item), self)
        return FromClause(*v(self.from_))

    def get_fields(self):
        fields = dict()
        if hasattr(self, 'fields') and self.fields is not None:
            for field in v(self.fields):
                if isinstance(field, str):
                    fields[field] = Field(field)
                elif isinstance(field, BaseField):
                    fields[field.name] = copy(field)
                else:
                    raise ModelError('invalid field: {!r}'.format(field), self)

        if 'id' in fields.keys():
            raise ModelError('illegal field name: "id"', self)
        elif 'type' in fields.keys():
            raise ModelError('illegal field name: "type"', self)

        id_field = Field('id', data_type=String)
        id_field.load(self)
        fields['id'] = id_field
        return fields

    def get_expr(self, col):
        expr = self.from_clause.get_column(col)
        if expr is None:
            raise ModelError('db column: {!r} not found'.format(col), self)
        return expr

    @classmethod
    def get_from_aliases(cls, name, *extra):
        from_ = deepcopy(list(cls.from_)) if isinstance(cls.from_, Sequence) else [copy(cls.from_)]
        from_.extend(extra)
        for i, from_item in enumerate(from_):
            alias_name = '_{}__{}_t'.format(name, from_item.name)
            if isinstance(from_item, FromItem):
                from_item.table = from_item.table.alias(alias_name)
            else:
                from_[i] = from_item.alias(alias_name)
        return from_

    def parse_arguments(self, args):
        try:
            return parse_arguments(args)
        except Error as e:
            raise APIError('request args | {}'.format(e), self)

    def attribute(self, name):
        if name in self.fields.keys() and not isinstance(self.fields[name], Relationship):
            return self.fields[name]
        raise ModelError('attribute does not exist: "{}"'.format(name), self)

    def relationship(self, name):
        if name in self.fields.keys() and isinstance(self.fields[name], Relationship):
            return self.fields[name]
        raise ModelError('relationship does not exist: "{}"'.format(name), self)

    ####################################################################################################################
    # properties
    ####################################################################################################################

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
        for from_item in self.from_clause:
            return get_primary_key(from_item.table)

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
                and (not field.exclude or field.sort_by)
                and field.expr is not None}

    @property
    def rec(self):
        return ColumnCollection(*self.from_clause().c.values()).as_immutable()

    ####################################################################################################################
    # core functionality
    ####################################################################################################################

    def init_schema(self, args=None, parents=()):

        for name, field in self.fields.items():

            fieldset_defined = args and args.fieldset_defined(self.type_)
            fieldset_wildcard = fieldset_defined and args.fieldset_wildcard(self.type_)
            in_fieldset = args and args.in_fieldset(self.type_, name)
            in_include = args and args.in_include(name, parents)
            in_sort = args and args.in_sort(name, parents)
            in_filter = args and args.in_filter(name, parents)
            field.sort_by = in_sort

            if isinstance(field, Field):
                field.exclude = name != 'id' and fieldset_defined and not (in_fieldset or fieldset_wildcard)
                if not field.exclude or in_sort or in_filter:
                    logger.info('load field: {}.{}'.format(self.name, field.name))
                    field.load(self)

            elif isinstance(field, Aggregate):
                field.exclude = not in_fieldset
                field.expr = None
                if in_fieldset or in_sort or in_filter:
                    logger.info('load field: {}.{}'.format(self.name, field.name))
                    field.load(self)

            elif isinstance(field, Relationship):
                field.exclude = not in_include
                if in_include or in_sort or in_filter:
                    logger.info('load field: {}.{}'.format(self.name, field.name))
                    field.load(self)
                    field.model.init_schema(args, tuple([*parents, field.name]))
            else:
                raise ModelError('unsupported field: {!r}'.format(field), self)

        schema = type('{}Schema'.format(self.name),
                      (JSONSchema,),
                      {name: field.get_ma_field() for name, field in self.fields.items() if not field.exclude})
        schema_registry[schema.__name__] = schema
        self.schema = schema()
        self.schema.context['root'] = self

    def response(self, data):
        response = dict(data=self.schema.dump(data, many=isinstance(data, list)))
        if len(self.included) > 0:
            response['included'] = reduce(lambda a, b: a + [rec for rec in b.values()], self.included.values(), list())
        if len(self.meta) > 0:
            response['meta'] = dict(self.meta)
        self.reset()
        return response

    def reset(self):
        self.included.clear()
        self.meta = dict()

    async def set_meta(self, limit, object_id=None, rel=None, **kwargs):
        filter_by = kwargs.get('filter_by', None)
        search_term = kwargs.get('search_term', None)
        is_related = object_id is not None and rel is not None
        if limit is not None or search_term is not None or filter_by:
            query = select_related(rel, object_id, count=True) if is_related else select_many(self, count=True)
            log_query(query)
            self.meta['total'] = await pg.fetchval(query)
            if limit is not None and filter_by:
                self.meta['totalFiltered'] = await pg.fetchval(
                    select_related(rel, object_id, filter_by=filter_by, count=True)
                    if is_related else select_many(self, filter_by=filter_by, count=True))
            if search_term is not None:
                self.meta['searchTerm'] = search_term
                if limit is not None:
                    self.meta['searchTotal'] = await pg.fetchval(
                        select_related(rel, object_id, search_term=search_term, count=True)
                        if is_related else select_many(self, search_term=search_term, count=True))

    def get_filter_by(self, args):
        filter_by = FilterBy()
        for arg in args.filter:
            custom_name = 'filter_{}'.format('_'.join(arg.path))
            if hasattr(self, custom_name):
                custom_filter = getattr(self, custom_name)
                op = arg.operator if arg.operator else 'eq'
                filter_by.add_custom('.'.join(arg.path), custom_filter(self.rec, arg.value, getattr(operator, op)))
            else:
                filter_by.add(self, arg)
        return filter_by

    def get_order_by(self, args):
        return OrderBy(self, *args.sort)

    async def fetch_included(self, data, args):

        if not isinstance(data, list):
            data = list() if data is None else [data]

        for rec in data:
            rec['type'] = self.type_

        for rel in self.relationships.values():
            result = list()
            for query in select_related(rel, [rec['id'] for rec in data]):
                log_query(query)
                result.extend(await pg.fetch(query))

            recs_by_parent_id = defaultdict(list)
            for rec in result:
                rec = dict(rec)
                parent_id = rec.pop('parent_id')
                recs_by_parent_id[parent_id].append(rec)

            for parent in data:
                parent_id = parent['id']
                if rel.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
                    parent[rel.name] = recs_by_parent_id[parent_id][0] if parent_id in recs_by_parent_id else None
                else:
                    parent[rel.name] = recs_by_parent_id[parent_id] if parent_id in recs_by_parent_id else list()

            await rel.model.fetch_included(
                reduce(lambda a, b: a + b if isinstance(b, list) else a + [b],
                       [rec[rel.name] for rec in data if rec[rel.name] is not None], list()), args)

    ####################################################################################################################
    # public interface
    ####################################################################################################################

    async def get_object(self, args, object_id):
        """
        Fetch a resource object.

        >>> from jsonapi.tests.model import UserModel
        >>> await UserModel().get_object({}, 1)
        {
            'data': {
                'id': '1',
                'type': 'user',
                'attributes': {
                    'email': 'dianagraham@fisher.com',
                    'first': 'Robert',
                    'last': 'Camacho'
                }
            }
        }
        >>> await UserModel().get_object({}, email='dianagraham@fisher.com')
        >>> await UserModel().get_object({}, first='Robert', last: 'Camacho'})

        :param dict args: a dictionary representing the request query string
        :param int|str|dict object_id: the resource object id
        :return: JSON API response document
        """
        args = self.parse_arguments(args)
        self.init_schema(args)

        if not await pg.fetchval(exists(self, object_id)):
            raise NotFound(object_id, self)

        query = select_one(self, object_id)
        log_query(query)
        result = await pg.fetchrow(query)
        if result is None:
            raise Forbidden(object_id, self)
        rec = dict(result)
        await self.fetch_included([rec], args)
        return self.response(rec)

    async def get_collection(self, args, **kwargs):
        """
        Fetch a collection of resources.

        >>> from jsonapi.tests.model import UserModel
        >>> await UserModel().get_collection({})
        {'data':
            [
                {'id': '1',
                 'type': 'user',
                 'attributes': {
                     'email': 'dianagraham@fisher.com',
                     'first': 'Robert',
                     'last': 'Camacho',
                     'createdOn': '2019-05-18T11:49:43Z',
                     'status': 'active',
                     'name': 'Robert Camacho'}
                 },
                ...
            ]
        }

        :param dict args: a dictionary representing the request query string
        :param str search: an optional search term
        :return: JSON API response document
        """
        args = self.parse_arguments(args)
        self.init_schema(args)
        filter_by, order_by = self.get_filter_by(args), self.get_order_by(args)
        search_term = kwargs.pop('search', None)
        query = select_many(self, filter_by=filter_by, order_by=order_by,
                            offset=args.page.offset, limit=args.page.limit,
                            search_term=search_term)
        log_query(query)
        recs = [dict(rec) for rec in await pg.fetch(query)]
        await self.set_meta(args.page.limit, filter_by=filter_by, search_term=search_term)
        await self.fetch_included(recs, args)
        return self.response(recs)

    async def get_related(self, args, object_id, relationship_name, **kwargs):
        """
        Fetch a collection of related resources.

        >>> from jsonapi.tests.model import ArticleModel
        >>> await ArticleModel().get_related({
        >>>     'include': 'articles.comments,articles.keywords',
        >>>     'fields[article]': 'title,body',
        >>>     'fields[comments]': 'body'
        >>> }, 1, 'author')

        :param dict args: a dictionary representing the request query string
        :param int|str|dict object_id: the resource object id
        :param str relationship_name: relationship name
        :param str search: an optional search term
        :return: JSON API response document
        """

        self.init_schema()
        if not await pg.fetchval(exists(self, object_id)):
            raise NotFound(object_id, self)

        rec = await pg.fetchrow(select_one(self, object_id))
        if rec is None:
            raise Forbidden(object_id, self)

        rel = self.relationship(relationship_name)
        args = self.parse_arguments(args)
        rel.load(self)
        rel.model.init_schema(args)
        filter_by, order_by = rel.model.get_filter_by(args), rel.model.get_order_by(args)
        search_term = kwargs.pop('search', None)
        query = select_related(rel, obj[self.primary_key.name], filter_by=filter_by, order_by=order_by,
                               offset=args.page.offset, limit=args.page.limit, search_term=search_term)
        log_query(query)
        if rel.cardinality in (Cardinality.ONE_TO_ONE, Cardinality.MANY_TO_ONE):
            result = await pg.fetchrow(query)
            data = dict(result) if result is not None else None
        else:
            data = [dict(rec) for rec in await pg.fetch(query)]
            await rel.model.set_meta(args.page.limit, obj[self.primary_key.name], rel,
                                     filter_by=filter_by, search_term=search_term)
        await rel.model.fetch_included(data, args)
        return rel.model.response(data)

    async def get_merged(self, args, object_id_list, relationship_name, **kwargs):
        self.init_schema()
        for object_id in object_id_list:
            if not await pg.fetchval(exists(self, object_id)):
                raise NotFound(object_id, self)

        recs = list()
        for object_id in object_id_list:
            rec = await pg.fetchrow(select_one(self, object_id))
            if rec is None:
                raise Forbidden(object_id, self)
            recs.append(rec)

        rel = self.relationship(relationship_name)
        if rel.cardinality != Cardinality.MANY_TO_MANY:
            raise APIError('get_merge works only with many-to-many relationships', self)

        args = self.parse_arguments(args)
        rel.load(self)
        rel.model.init_schema(args)
        filter_by, order_by = rel.model.get_filter_by(args), rel.model.get_order_by(args)
        query = select_merged(self, rel, set(rec['id'] for rec in recs),
                              filter_by=filter_by, order_by=order_by,
                              offset=args.page.offset, limit=args.page.limit,
                              exclude=set(kwargs.pop('exclude', ())), options=args.merge)
        log_query(query)
        data = [dict(rec) for rec in await pg.fetch(query)]
        # await rel.model.set_meta(args.page.limit, obj[self.primary_key.name], rel,
        #                          filter_by=filter_by, search_term=search_term)
        await rel.model.fetch_included(data, args)
        return rel.model.response(data)

    def __repr__(self):
        return '<Model({})>'.format(self.name)


########################################################################################################################
# Multi-Model Functions
########################################################################################################################


class ModelSet(Set):

    def __init__(self, *models, searchable=False):

        if len(models) < 2:
            raise Error('at least two models are required')

        models_uniq = list(set(models))
        if len(models) > len(models_uniq):
            raise Error('models must be unique')

        for i, model in enumerate(models_uniq):
            if isinstance(model, type) and issubclass(model, Model):
                models_uniq[i] = model()
            elif not isinstance(model, Model):
                raise Error('invalid model: {!r}'.format(model))

        if searchable:
            for model in models_uniq:
                if model.search is None:
                    raise Error('model must be searchable: {!r}'.format(model))

        self._models = set(models_uniq)

    def __iter__(self):
        return iter(self._models)

    def __contains__(self, item):
        return item in self._models

    def __len__(self):
        return len(self._models)

    def __repr__(self):
        return '{' + ','.join(model.name for model in self._models) + '}'


def _extract_model_args(model, args):
    model_args = dict()
    include_key = 'include[{}]'.format(model.type_)
    if include_key in args:
        model_args['include'] = args[include_key]
    for key, val in args.items():
        if key.startswith('fields'):
            model_args[key] = val
    return model_args


async def get_collection(args, *models, **kwargs):
    """
    Fetch a heterogeneous collection of objects.

    Returns a heterogeneous list of objects.

    >>> from jsonapi.model import search
    >>> search({'include[user]': 'bio',
    >>>         'include[article]': 'keywords,author.bio,publisher.bio',
    >>>         'fields[user]': 'name,email',
    >>>         'fields[user-bio]': 'birthday,age',
    >>>         'fields[article]': 'title'},
    >>>         'John', UserModel, ArticleModel)

    :param dict args: a dictionary representing the request query string
    :param mixed models: variable length list of model classes or instances
    :param str search: a PostgreSQL full text search query string (e.x. ``'foo:* & !bar'``)
    :return: JSON API response document
    """
    ra = parse_arguments(args)
    search_term = kwargs.pop('search', None)
    models = ModelSet(*models, searchable=search_term is not None)
    query = select_mixed(models, order_by=ra.sort, limit=ra.page.limit, offset=ra.page.offset) \
        if search_term is None else search_query(models, search_term, limit=ra.page.limit, offset=ra.page.offset)
    log_query(query)
    mixed = list()
    async with pg.query(query) as cursor:
        async for row in cursor:
            mixed.append(dict(type=row['resource_type'], id=row['id']))

    data = defaultdict(dict)
    included = defaultdict(dict)
    meta = {'total': 0, 'subTotal': dict()}
    for model in models:
        object_id = list(obj['id'] for obj in mixed if model.type_ == obj['type'])
        if len(object_id) > 0:
            model_args = model.parse_arguments(_extract_model_args(model, args))
            model.init_schema(model_args)
            query = select_many(model, filter_by=FilterBy(
                model.primary_key.in_([cast(x, model.primary_key.type) for x in object_id])))
            log_query(query)
            recs = [{'type': model.type_, **rec} for rec in await pg.fetch(query)]
            await model.fetch_included(recs, model_args)
            for rec in model.schema.dump(recs, many=True):
                data[rec['type']][rec['id']] = rec
            if len(model.included) > 0:
                for resource_type in model.included.keys():
                    included[resource_type].update(model.included[resource_type])
        model.reset()

    for (resource_type, query) in (select_mixed(models, count=True) \
            if search_term is None else search_query(models, search_term, count=True)):
        meta['subTotal'][resource_type] = await pg.fetchval(query)
        meta['total'] += meta['subTotal'][resource_type]
    return dict(data=[data[rec['type']][str(rec['id'])] for rec in mixed],
                included=reduce(lambda a, b: a + [r for r in b.values()], included.values(), list()),
                meta=meta)
