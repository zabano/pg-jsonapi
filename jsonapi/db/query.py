import sqlalchemy.sql as sql

from jsonapi.exc import ModelError, APIError
from jsonapi.fields import Aggregate, Derived, Field
from .table import Cardinality, FromClause, FromItem, get_foreign_key_pair

SQL_PARAM_LIMIT = 10000
SEARCH_LABEL = '_ts_rank'


####################################################################################################
# public interface
####################################################################################################

def exists(model, obj_id):
    return sql.select([sql.exists(sql.select([model.primary_key]).where(
        model.primary_key == obj_id))])


def select_one(model, obj_id):
    query = sql.select(from_obj=_from_obj(model),
                       columns=_col_list(model),
                       whereclause=model.primary_key == obj_id)
    query = _group_query(model, query)
    query = _protect_query(model, query)
    return query


def select_many(model, **kwargs):
    filter_by = kwargs.get('filter_by', None)
    order_by = kwargs.get('order_by', None)
    search_term = kwargs.get('search_term', None)
    count = bool(kwargs.get('count', False))
    limit = kwargs.get('limit', None)
    offset = kwargs.get('offset', 0)

    if filter_by and search_term:
        raise APIError('cannot filter and search at the same time', model)

    query = sql.select(columns=_col_list(model, search_term=search_term),
                       from_obj=_from_obj(model,
                                          filter_by=filter_by,
                                          order_by=order_by,
                                          search_term=search_term))

    if not count:
        query = _protect_query(model, query)
        query = _sort_query(model, query, order_by, search_term)
        if limit is not None:
            query = query.offset(offset).limit(limit)

    query = _group_query(model, query, filter_by=filter_by, order_by=order_by)
    query = _filter_query(query, filter_by)
    query = _search_query(model, query, search_term)
    return _count_query(query) if count else query


def select_related(rel, obj_id, **kwargs):
    filter_by = kwargs.get('filter_by', None)
    order_by = kwargs.get('order_by', None)
    search_term = kwargs.get('search_term', None)
    count = bool(kwargs.get('count', False))
    limit = kwargs.get('limit', None)
    offset = kwargs.get('offset', 0)

    if filter_by and search_term:
        raise APIError('cannot filter and search at the same time', rel.model)

    from_items = []

    if rel.cardinality == Cardinality.ONE_TO_ONE:
        parent_col = rel.model.primary_key
        if isinstance(obj_id, list):
            from_items.append(FromItem(
                rel.model.primary_key.table,
                onclause=rel.model.primary_key == rel.parent.primary_key,
                left=True))

    elif rel.cardinality == Cardinality.ONE_TO_MANY:
        parent_col = rel.model.get_expr(rel.ref)

    elif rel.cardinality == Cardinality.MANY_TO_ONE:
        parent_col = rel.parent.primary_key
        from_items.append(FromItem(
            rel.parent.primary_key.table,
            onclause=rel.model.primary_key == rel.parent.get_expr(rel.ref),
            left=True))

    else:
        ref_col, parent_col = get_foreign_key_pair(rel.model, *rel.ref)
        from_items.append(FromItem(
            ref_col.table,
            onclause=rel.model.primary_key == ref_col,
            left=True))

    query = sql.select(columns=_col_list(rel.model,
                                         parent_col.label('parent_id')
                                         if isinstance(obj_id, list) else None,
                                         search_term=search_term),
                       from_obj=_from_obj(rel.model, *from_items,
                                          filter_by=filter_by,
                                          order_by=order_by,
                                          search_term=search_term))
    if not isinstance(obj_id, list):
        query = query.where(parent_col == obj_id)

    if not count:
        query = _protect_query(rel.model, query)
        if rel.cardinality in (Cardinality.ONE_TO_MANY, Cardinality.MANY_TO_MANY):
            query = _sort_query(rel.model, query, order_by, search_term)
        if limit is not None:
            query = query.offset(offset).limit(limit)

    query = _group_query(rel.model, query, parent_col if isinstance(obj_id, list) else None,
                         filter_by=filter_by, order_by=order_by)
    query = _filter_query(query, filter_by)
    query = _search_query(rel.model, query, search_term)
    # query = query.distinct()

    if isinstance(obj_id, list):
        return (query.where(parent_col.in_(x))
                for x in (obj_id[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(obj_id), SQL_PARAM_LIMIT)))
    return _count_query(query) if count else query


def search_query(model, term):
    query = sql.select(columns=[model.primary_key, _rank_column(model, term)],
                       from_obj=_from_obj(model, model.search))
    query = _search_query(model, query, term)
    return _protect_query(model, query)


####################################################################################################
# helpers
####################################################################################################

def _col_list(model, *extra_columns, **kwargs):
    group_by = bool(kwargs.get('group_by', False))
    col_list = [model.attributes['id'].expr.label('id')]
    for field in model.attributes.values():
        if (isinstance(field, (Field, Derived)) and field.name != 'id') \
                or (not group_by and isinstance(field, Aggregate) and field.expr is not None):
            col_list.append(field.expr.label(field.name))
    col_list.extend(col for col in extra_columns if col is not None)
    return col_list


def _from_obj(model, *extra_items, **kwargs):
    filter_by = kwargs.get('filter_by', None)
    order_by = kwargs.get('order_by', None)
    search_term = kwargs.get('search_term', None)
    from_clause = FromClause(*model.from_clause)
    from_clause.extend(extra_items)
    if filter_by:
        from_clause.extend(filter_by.from_items)
        from_clause.extend(filter_by.from_items_last)
    if order_by:
        from_clause.extend(order_by.from_items)
    if model.search is not None and search_term is not None:
        from_clause.append(model.search)
    for field in model.attributes.values():
        if isinstance(field, Aggregate) and field.expr is not None:
            for from_item in field.from_items[model.name]:
                from_clause.append(from_item)
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
        return query.order_by(*order_by.exprs)
    return query


def _protect_query(model, query):
    if model.access is None:
        return query
    if not hasattr(model, 'user'):
        raise ModelError('"user" not defined for protected model', model)
    return query.where(model.access(
        model.primary_key, model.user.id if model.user else None))


def _search_query(model, query, search_term):
    if model.search is None or search_term is None:
        return query
    return query.where(model.search.c.tsvector.match(search_term))


def _rank_column(model, search_term):
    return sql.func.ts_rank_cd(
        model.search.c.tsvector, sql.func.to_tsquery(search_term)).label(SEARCH_LABEL)


def _count_query(query):
    return sql.select([sql.func.count()]).select_from(query.alias('count'))
