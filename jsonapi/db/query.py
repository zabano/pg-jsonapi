import sqlalchemy.sql as sql

from jsonapi.exc import APIError, ModelError
from jsonapi.fields import Aggregate, Field
from .table import Cardinality, FromClause, FromItem, get_primary_key

SQL_PARAM_LIMIT = 10000
SEARCH_LABEL = '_ts_rank'


class QueryArguments:

    def __init__(self, **kwargs):
        self.filter_by = kwargs.get('filter_by', None)
        self.order_by = kwargs.get('order_by', None)
        self.search_term = kwargs.get('search_term', None)
        self.count = bool(kwargs.get('count', False))
        self.limit = kwargs.get('limit', None)
        self.offset = kwargs.get('offset', 0)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               ','.join('{}={}'.format(k, v) for k, v in self.__dict__.items() if v))


########################################################################################################################
# public interface
########################################################################################################################

def exists(model, obj_id):
    return sql.select([sql.exists(sql.select([model.primary_key]).where(_where_one(model, obj_id)))])


def select_one(model, obj_id):
    query = sql.select(from_obj=_from_obj(model), columns=_col_list(model), whereclause=_where_one(model, obj_id))
    query = _group_query(model, query)
    query = _protect_query(model, query)
    return query


def select_many(model, **kwargs):
    qa = QueryArguments(**kwargs)
    if qa.filter_by and qa.search_term:
        raise APIError('cannot filter and search at the same time', model)
    query = sql.select(columns=_col_list(model, search_term=qa.search_term),
                       from_obj=_from_obj(model, filter_by=qa.filter_by, order_by=qa.order_by,
                                          search_term=qa.search_term))
    if not qa.count:
        query = _protect_query(model, query)
        query = _sort_query(model, query, qa.order_by, qa.search_term)
        if qa.limit is not None:
            query = query.offset(qa.offset).limit(qa.limit)
    query = _group_query(model, query, filter_by=qa.filter_by, order_by=qa.order_by)
    query = _filter_query(query, qa.filter_by)
    query = _search_query(model, query, qa.search_term)
    return _count_query(query) if qa.count else query


def select_related(rel, obj_id, **kwargs):
    qa = QueryArguments(**kwargs)
    if qa.filter_by and qa.search_term:
        raise APIError('cannot filter and search at the same time', rel.model)
    parent_col = rel.parent_col.label('parent_id') if isinstance(obj_id, list) else None
    query = sql.select(columns=_col_list(rel.model, parent_col, search_term=qa.search_term),
                       from_obj=_from_obj(rel.model, *rel.get_from_items(True), filter_by=qa.filter_by,
                                          order_by=qa.order_by, search_term=qa.search_term))
    if not isinstance(obj_id, list):
        query = query.where(rel.parent_col == obj_id)
    if not qa.count:
        query = _protect_query(rel.model, query)
        if rel.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
            query = _sort_query(rel.model, query, qa.order_by, qa.search_term)
        if qa.limit is not None:
            query = query.offset(qa.offset).limit(qa.limit)
    query = _group_query(rel.model, query, parent_col, filter_by=qa.filter_by, order_by=qa.order_by)
    query = _filter_query(query, qa.filter_by)
    query = _search_query(rel.model, query, qa.search_term)
    if isinstance(obj_id, list):
        return (query.where(rel.parent_col.in_(x))
                for x in (obj_id[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(obj_id), SQL_PARAM_LIMIT)))
    return _count_query(query) if qa.count else query


def select_mixed(models, **kwargs):
    qa = QueryArguments(**kwargs)
    if qa.count:
        return ((model.type_, _count_query(_protect_query(
            model, sql.select([model.primary_key])))) for model in models)
    queries = list()
    for model in models:
        queries.append(_protect_query(model, sql.select([
            model.primary_key.label('id'), model.primary_key.table,
            sql.func.lower(model.type_).label('resource_type')])))
    union = sql.union(*queries)
    if qa.limit is not None:
        union = union.limit(qa.limit).offset(qa.offset)
    return union.order_by(*[getattr(union.c[s.path[0]], 'desc' if s.desc else 'asc')() for s in qa.order_by])


def search_query(models, term, **kwargs):
    qa = QueryArguments(**kwargs)
    if qa.count:
        return ((model.type_, _count_query(_protect_query(
            model, sql.select([model.primary_key])))) for model in models)
    queries = list()
    for model in models:
        query = sql.select(columns=[model.primary_key.label('id'),
                                    sql.func.lower(model.type_).label('resource_type'),
                                    _rank_column(model, term)],
                           from_obj=_from_obj(model, search_term=term))
        query = _search_query(model, query, term)
        queries.append(_protect_query(model, query))

    union = sql.union(*queries)
    if qa.limit is not None:
        union = union.limit(qa.limit).offset(qa.offset)
    return union.order_by(union.c[SEARCH_LABEL].desc())


########################################################################################################################
# helpers
########################################################################################################################

def _where_one(model, obj_id):
    return sql.and_(model.fields[name].expr == val for name, val in obj_id.items()) \
        if isinstance(obj_id, dict) else model.primary_key == obj_id


def _col_list(model, *extra_columns, **kwargs):
    group_by = bool(kwargs.get('group_by', False))
    col_list = [model.attributes['id'].expr.label('id')]
    for field in model.attributes.values():
        if (isinstance(field, Field) and field.name != 'id') \
                or (not group_by and isinstance(field, Aggregate) and field.expr is not None):
            col_list.append(field.expr.label(field.name))
    col_list.extend(col for col in extra_columns if col is not None)
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
    if (filter_by is not None and len(filter_by.having) > 0) \
            or (order_by is not None and order_by.distinct) \
            or (any(isinstance(field, Aggregate) for field in model.attributes.values())):
        columns = list(extra_columns)
        if order_by:
            columns.extend(order_by.group_by)
        query = query.group_by(*_col_list(model, *columns, group_by=True))
    return query


def _filter_query(query, filter_by):
    if not filter_by:
        return query
    if filter_by.where:
        query = query.where(sql.and_(*filter_by.where))
    if filter_by.having:
        query = query.having(sql.and_(*filter_by.having))
    if filter_by.distinct:
        query = query.distinct()
    return query


def _sort_query(model, query, order_by, search_term):
    if search_term is not None:
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


def _search_query(model, query, search_term):
    if model.search is None or search_term is None:
        return query
    return query.where(model.search.c.tsvector.match(search_term))


def _rank_column(model, search_term):
    return sql.func.ts_rank_cd(model.search.c.tsvector, sql.func.to_tsquery(search_term)).label(SEARCH_LABEL)


def _count_query(query):
    return sql.select([sql.func.count()]).select_from(query.alias('count'))
