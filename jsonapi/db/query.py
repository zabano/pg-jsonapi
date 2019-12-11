import operator

import sqlalchemy as sa

from jsonapi.exc import APIError, ModelError
from jsonapi.fields import Aggregate, Field
from .table import Cardinality, FromClause, FromItem, get_primary_key

SQL_PARAM_LIMIT = 10000
SEARCH_LABEL = '_ts_rank'


class QueryArguments:

    def __init__(self, **kwargs):
        self.where = kwargs.get('where', None)
        self.filter_by = kwargs.get('filter_by', None)
        self.order_by = kwargs.get('order_by', None)
        self.search_term = kwargs.get('search_term', None)
        self.count = bool(kwargs.get('count', False))
        self.limit = kwargs.get('limit', None)
        self.offset = kwargs.get('offset', 0)
        self.exclude = set(kwargs.get('exclude', set()))
        self.options = kwargs.get('options', None)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               ','.join('{}={}'.format(k, v) for k, v in self.__dict__.items() if v))


########################################################################################################################
# public interface
########################################################################################################################

def exists(model, obj_id):
    return sa.select([sa.exists(sa.select([model.primary_key]).where(_where_one(model, obj_id)))])


def select_one(model, obj_id):
    query = sa.select(from_obj=_from_obj(model), columns=_col_list(model), whereclause=_where_one(model, obj_id))
    query = _group_query(model, query)
    query = _protect_query(model, query)
    return query


def select_many(model, **kwargs):
    qa = QueryArguments(**kwargs)
    query = sa.select(columns=_col_list(model, order_by=qa.order_by, search_term=qa.search_term),
                      from_obj=_from_obj(model, filter_by=qa.filter_by, order_by=qa.order_by,
                                         search_term=qa.search_term))
    if qa.where is not None:
        query = query.where(qa.where)

    query = _protect_query(model, query)
    if not qa.count:
        query = _sort_query(model, query, qa.order_by, qa.search_term)
        if qa.limit is not None:
            query = query.offset(qa.offset).limit(qa.limit)
    query = _group_query(model, query, filter_by=qa.filter_by, order_by=qa.order_by, search_term=qa.search_term)
    query = _filter_query(query, qa.filter_by, qa.limit)
    query = _search_query(model, query, qa.search_term)
    return _count_query(query) if qa.count else query


def select_related(rel, obj_id, **kwargs):
    qa = QueryArguments(**kwargs)
    parent_col = rel.parent_col.label('parent_id') if isinstance(obj_id, list) else None
    query = sa.select(columns=_col_list(rel.model, parent_col, order_by=qa.order_by, search_term=qa.search_term),
                      from_obj=_from_obj(rel.model, *rel.get_from_items(True), filter_by=qa.filter_by,
                                         order_by=qa.order_by, search_term=qa.search_term))
    if qa.where is not None:
        query = query.where(qa.where)
    if not isinstance(obj_id, list):
        query = query.where(rel.parent_col == obj_id)

    query = _protect_query(rel.model, query)
    if not qa.count:
        if rel.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
            query = _sort_query(rel.model, query, qa.order_by, qa.search_term)
        if qa.limit is not None:
            query = query.offset(qa.offset).limit(qa.limit)
    query = _group_query(rel.model, query, parent_col,
                         filter_by=qa.filter_by, order_by=qa.order_by, search_term=qa.search_term)
    query = _filter_query(query, qa.filter_by, qa.limit)
    query = _search_query(rel.model, query, qa.search_term)
    if isinstance(obj_id, list):
        return (query.where(rel.parent_col.in_(x))
                for x in (obj_id[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(obj_id), SQL_PARAM_LIMIT)))
    return _count_query(query) if qa.count else query


def select_merged(model, rel, obj_ids, **kwargs):
    qa = QueryArguments(**kwargs)
    query = sa.select(columns=_col_list(rel.model),
                      from_obj=_from_obj(rel.model, *rel.get_from_items(True),
                                         filter_by=qa.filter_by, order_by=qa.order_by))
    if not qa.exclude.issubset(obj_ids):
        raise APIError('merge | invalid "exclude" value: {!r}'.format(qa.exclude), model)

    obj_ids = set(obj_ids)
    include = obj_ids - qa.exclude

    query = query.where(model.primary_key.in_(obj_ids))

    array = sa.func.array
    array_length = sa.func.array_length
    array_agg = sa.func.array_agg
    coalesce = sa.func.coalesce
    unnest = sa.func.unnest

    merge_count = qa.options.merge_count if qa.options and qa.options.merge_count else len(include)
    merge_op = qa.options.merge_operator if qa.options else operator.eq
    exc_count = qa.options.exclude_count if qa.options and qa.options.exclude_count else len(qa.exclude)
    exc_op = qa.options.exclude_operator if qa.options else operator.eq

    merge_col = rel.refs[0].distinct()
    arr_len_merged = array_length(array(sa.select('*').select_from(unnest(array_agg(merge_col))).except_(
        sa.select([unnest(sa.cast(qa.exclude, sa.ARRAY(sa.Integer)))]))), sa.text('1'))
    if len(qa.exclude) > 0:
        arr_len_excluded = coalesce(array_length(array(sa.select('*').select_from(unnest(array_agg(merge_col))).except_(
            sa.select([unnest(sa.cast(include, sa.ARRAY(sa.Integer)))]))), sa.text('1')), sa.text('0'))
        query = query.having(sa.and_(merge_op(arr_len_merged, merge_count), exc_op(arr_len_excluded, exc_count)))
    else:
        query = query.having(merge_op(arr_len_merged, merge_count))

    query = _group_query(rel.model, query, filter_by=qa.filter_by, order_by=qa.order_by, force=True)
    query = _filter_query(query, qa.filter_by, qa.limit)
    query = _protect_query(rel.model, query)
    if not qa.count:
        query = _sort_query(rel.model, query, qa.order_by, qa.search_term)
        if qa.limit is not None:
            query = query.offset(qa.offset).limit(qa.limit)
    return _count_query(query) if qa.count else query


def select_mixed(models, **kwargs):
    qa = QueryArguments(**kwargs)
    if qa.count:
        return ((model.type_, _count_query(_protect_query(
            model, sa.select([model.primary_key])))) for model in models)
    queries = list()
    for model in models:
        queries.append(_protect_query(model, sa.select([
            model.primary_key.label('id'), model.primary_key.table,
            sa.func.lower(model.type_).label('resource_type')])))
    union = sa.union(*queries)
    if qa.limit is not None:
        union = union.limit(qa.limit).offset(qa.offset)
    return union.order_by(*[getattr(union.c[s.path[0]], 'desc' if s.desc else 'asc')() for s in qa.order_by])


def search_query(models, term, **kwargs):
    qa = QueryArguments(**kwargs)
    if qa.count:
        return ((model.type_, _count_query(_protect_query(
            model, sa.select([model.primary_key])))) for model in models)
    queries = list()
    for model in models:
        query = sa.select(columns=[model.primary_key.label('id'),
                                   sa.func.lower(model.type_).label('resource_type'),
                                   _rank_column(model, term)],
                          from_obj=_from_obj(model, search_term=term))
        query = _search_query(model, query, term)
        queries.append(_protect_query(model, query))

    union = sa.union(*queries)
    if qa.limit is not None:
        union = union.limit(qa.limit).offset(qa.offset)
    return union.order_by(union.c[SEARCH_LABEL].desc())


########################################################################################################################
# helpers
########################################################################################################################

def _where_one(model, obj_id):
    if isinstance(obj_id, dict):
        return sa.and_(model.fields[name].expr == sa.cast(val, model.fields[name].expr.type)
                       for name, val in obj_id.items())
    return model.primary_key == sa.cast(obj_id, model.primary_key.type)


def _col_list(model, *extra_columns, **kwargs):
    group_by = bool(kwargs.get('group_by', False))
    order_by = kwargs.get('order_by', None)
    col_list = [model.attributes['id'].expr.label('id')]
    for field in model.attributes.values():
        if (isinstance(field, Field) and field.name != 'id') \
                or (not group_by and isinstance(field, Aggregate) and field.expr is not None):
            col_list.append(field.expr.label(field.name))
    col_list.extend(col for col in extra_columns if col is not None)
    if order_by:
        col_list.extend([col.label('_sort_{:d}'.format(i)) for i, col in enumerate(order_by.group_by)])
    return col_list


def _from_obj(model, *extra_items, **kwargs):
    filter_by = kwargs.get('filter_by', None)
    order_by = kwargs.get('order_by', None)
    search_term = kwargs.get('search_term', None)
    from_clause = FromClause(*model.from_clause)
    from_clause.add(*extra_items)
    if filter_by:
        from_clause.add(*filter_by.from_items)
    if order_by:
        from_clause.add(*order_by.from_items)
    if model.search is not None and search_term is not None:
        from_clause.add(FromItem(model.search, onclause=model.primary_key == get_primary_key(model.search)))
    for field in model.attributes.values():
        if isinstance(field, Aggregate) and field.expr is not None:
            for from_item in field.from_items[model.name]:
                from_clause.add(from_item)
    return from_clause()


def _group_query(model, query, *extra_columns, **kwargs):
    filter_by = kwargs.get('filter_by', None)
    order_by = kwargs.get('order_by', None)
    search_term = kwargs.get('search_term', None)
    force = bool(kwargs.get('force', False))
    if force or (filter_by is not None and len(filter_by.having) > 0) \
            or (order_by is not None and order_by.distinct) \
            or (any(isinstance(field, Aggregate) for field in model.attributes.values())):
        columns = list(extra_columns)
        if order_by:
            columns.extend(order_by.group_by)
        if search_term:
            columns.append(model.search.c.tsvector)
        query = query.group_by(*_col_list(model, *columns, group_by=True))
    return query


def _filter_query(query, filter_by, limit):
    if not filter_by:
        return query
    if filter_by.where:
        query = query.where(sa.and_(*filter_by.where))
    if filter_by.having:
        query = query.having(sa.and_(*filter_by.having))
    if filter_by.distinct and limit is not None:
        query = query.distinct()
    return query


def _sort_query(model, query, order_by, search_term):
    if search_term is not None and not order_by:
        return query.order_by(_rank_column(model, search_term).desc())
    if order_by:
        return query.order_by(*order_by)
    return query


def _protect_query(model, query):
    if model.access is None:
        return query
    if not hasattr(model, 'user'):
        raise ModelError('"user" not defined for protected model', model)
    return query.where(model.access(model.primary_key, model.user.id if model.user else None))


def _search_term(search_term):
    if ' ' in search_term:
        return sa.func.cast(sa.func.plainto_tsquery(search_term), sa.Text)
    return search_term


def _search_query(model, query, search_term):
    if model.search is None or search_term is None:
        return query
    return query.where(model.search.c.tsvector.match(_search_term(search_term)))


def _rank_column(model, search_term):
    return sa.func.ts_rank_cd(model.search.c.tsvector,
                              sa.func.to_tsquery(_search_term(search_term))).label(SEARCH_LABEL)


def _count_query(query):
    return sa.select([sa.func.count()]).select_from(query.alias('count'))
