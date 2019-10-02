from copy import copy

import sqlalchemy as sa

from jsonapi.exc import APIError, ModelError
from jsonapi.fields import Aggregate, Field
from .filter import Filter
from .table import FromItem, MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE
from .util import get_primary_key

SQL_PARAM_LIMIT = 10000


class Query:
    """
    Represents a SELECT query.
    """

    def __init__(self, model):
        self.model = model

    def is_aggregate(self):
        return any(isinstance(field, Aggregate) for field in self.model.fields.values()
                   if field.expr is not None)

    def col_list(self, group_by=False, search=None):
        col_list = [field.expr.label(name)
                    for name, field in self.model.attributes.items()
                    if isinstance(field, Field if group_by else (Field, Aggregate))]
        if self.model.search is not None and search is not None:
            col_list.append(self.rank_column(search))
        return col_list

    def from_obj(self, *additional):
        from_clause = copy(self.model.from_clause)
        from_clause.extend(additional)
        for field in self.model.fields.values():
            if isinstance(field, Aggregate) and field.expr is not None:
                for from_item in field.from_items:
                    from_clause.append(from_item)
        return from_clause()

    def rank_column(self, search):
        if self.model.search is not None and search is not None:
            return sa.func.ts_rank_cd(
                self.model.search.c.tsvector, sa.func.to_tsquery(search)).label('_ts_rank')

    def group_by(self, query, *columns):
        if self.is_aggregate():
            query = query.group_by(*[*self.col_list(group_by=True), *columns])
        return query

    def sort_by(self, query, search=None):
        if self.model.search is not None and search is not None:
            return query.order_by(self.rank_column(search).desc())
        order_by = list()
        for name, desc in self.model.args.sort.items():
            try:
                expr = self.model.fields[name].expr
            except KeyError:
                raise APIError('column does not exist: {}'.format(name), self.model)
            else:
                order_by.append(getattr(expr, 'desc' if desc else 'asc')().nullslast())
        return query.order_by(*order_by)

    def check_access(self, query):

        if self.model.access is None:
            return query

        if not hasattr(self.model, 'user'):
            raise ModelError('"user" not defined for protected model', self.model)

        return query.where(self.model.access(
            self.model.primary_key, self.model.user.id if self.model.user else None))

    def _search(self, query, search):
        if self.model.search is None or search is None:
            return query
        query = query.where(self.model.search.c.tsvector.match(search))
        return query

    def exists(self, resource_id):
        return sa.select([sa.exists(sa.select([self.model.primary_key]).where(
            self.model.primary_key == resource_id))])

    def get(self, resource_id):
        query = sa.select(from_obj=self.from_obj(),
                          columns=self.col_list(),
                          whereclause=self.model.primary_key == resource_id)
        query = self.group_by(query)
        if self.model.access is not None:
            query = self.check_access(query)
        return query

    def all(self, filter_by=None, paginate=True, count=False, search=None):

        search_t = self.model.search
        from_obj = self.from_obj(search_t) if search is not None else self.from_obj()
        query = sa.select(columns=self.col_list(search=search), from_obj=from_obj)
        query = self.group_by(query)

        if not count:
            query = self.sort_by(query, search)

        if filter_by is not None:
            if isinstance(filter_by, Filter):
                if filter_by.where:
                    query = query.where(sa.and_(*filter_by.where))
                if filter_by.having:
                    query = query.having(sa.and_(*filter_by.having))
            else:
                return query.where(filter_by)

        query = self.check_access(query)

        if paginate and self.model.args.limit is not None:
            query = query.offset(self.model.args.offset).limit(self.model.args.limit)

        query = self._search(query, search)

        return query.alias('count').count() if count else query

    def search(self, term):
        search_t = self.model.search
        query = sa.select(columns=[self.model.primary_key, self.rank_column(term)],
                          from_obj=self.from_obj(search_t))
        query = self._search(query, term)
        return self.check_access(query)

    def related(self, resource_id, rel):
        pkey_column = get_primary_key(rel.fkey.parent.table)
        where_col = pkey_column if rel.cardinality in (ONE_TO_ONE, MANY_TO_ONE) \
            else rel.fkey.parent
        query = sa.select(columns=self.col_list(),
                          from_obj=self.from_obj(
                              FromItem(rel.fkey.parent.table,
                                       onclause=rel.fkey.column == rel.fkey.parent,
                                       left=True)),
                          whereclause=where_col == resource_id)
        query = self.group_by(query)
        if rel.cardinality in (ONE_TO_MANY, MANY_TO_MANY):
            query = self.sort_by(query)
        query = self.check_access(query)
        return query

    def included(self, rel, id_list):
        where_col = get_primary_key(rel.fkey.parent.table) \
            if rel.cardinality is MANY_TO_ONE else rel.fkey.parent
        query = sa.select(columns=[*self.col_list(), where_col.label('parent_id')],
                          from_obj=self.from_obj(
                              FromItem(rel.fkey.parent.table,
                                       onclause=rel.fkey.column == rel.fkey.parent,
                                       left=True)))
        query = self.group_by(query, where_col)
        query = self.check_access(query)
        return (query.where(where_col.in_(x))
                for x in (id_list[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(id_list), SQL_PARAM_LIMIT)))
