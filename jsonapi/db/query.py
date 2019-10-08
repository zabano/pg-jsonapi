from copy import copy

from sqlalchemy.sql import and_, exists, func, select

from jsonapi.exc import APIError, ModelError
from jsonapi.fields import Aggregate, Field
from .table import FromItem, MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE, get_table_name

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
            return func.ts_rank_cd(
                self.model.search.c.tsvector, func.to_tsquery(search)).label('_ts_rank')

    ################################################################################################
    # query
    ################################################################################################

    def group_query(self, query, *columns):
        if self.is_aggregate():
            query = query.group_by(*[*self.col_list(group_by=True), *columns])
        return query

    @staticmethod
    def filter_query(query, filter_by):
        if not filter_by:
            return query
        if filter_by.where:
            query = query.where(and_(*filter_by.where))
        if filter_by.having:
            query = query.having(and_(*filter_by.having))
        return query

    def sort_query(self, args, query, search=None):
        if self.model.search is not None and search is not None:
            return query.order_by(self.rank_column(search).desc())
        order_by = list()
        for name, desc in args.sort.items():
            try:
                expr = self.model.fields[name].expr
            except KeyError:
                raise APIError('column does not exist: {}'.format(name), self.model)
            else:
                order_by.append(getattr(expr, 'desc' if desc else 'asc')().nullslast())
        return query.order_by(*order_by)

    def protect_query(self, query):

        if self.model.access is None:
            return query

        if not hasattr(self.model, 'user'):
            raise ModelError('"user" not defined for protected model', self.model)

        return query.where(self.model.access(
            self.model.primary_key, self.model.user.id if self.model.user else None))

    def search_query(self, query, search):
        if self.model.search is None or search is None:
            return query
        query = query.where(self.model.search.c.tsvector.match(search))
        return query

    ################################################################################################
    # interface
    ################################################################################################

    def exists(self, resource_id):
        return select([exists(select([self.model.primary_key]).where(
            self.model.primary_key == resource_id))])

    def get(self, resource_id):
        query = select(from_obj=self.from_obj(),
                       columns=self.col_list(),
                       whereclause=self.model.primary_key == resource_id)
        query = self.group_query(query)
        if self.model.access is not None:
            query = self.protect_query(query)
        return query

    def all(self, args, filter_by=None, paginate=True, count=False, search=None):
        search_t = self.model.search
        from_items = list(filter_by.from_items) if filter_by else list()
        if search is not None:
            from_items.append(search_t)
        query = select(columns=self.col_list(search=search), from_obj=self.from_obj(*from_items))

        query = self.group_query(query)
        if not count:
            query = self.sort_query(args, query, search)

        query = self.filter_query(query, filter_by)
        query = self.protect_query(query)

        if paginate and args.limit is not None:
            query = query.offset(args.offset).limit(args.limit)

        query = self.search_query(query, search)

        if count:
            return select([func.count()]).select_from(query.alias('count'))
        return query

    def search(self, term):
        search_t = self.model.search
        query = select(columns=[self.model.primary_key, self.rank_column(term)],
                       from_obj=self.from_obj(search_t))
        query = self.search_query(query, term)
        return self.protect_query(query)

    def related(self, resource_id, rel, args,
                filter_by=None, paginate=True, count=False, search=None):

        if rel.cardinality == ONE_TO_ONE:
            where_col = rel.model.primary_key
            from_item = None
        elif rel.cardinality == ONE_TO_MANY:
            where_col = rel.model.get_db_column(rel.ref)
            from_item = None
        elif rel.cardinality == MANY_TO_ONE:
            where_col = rel.parent.primary_key
            from_item = FromItem(
                rel.parent.primary_key.table,
                onclause=rel.model.primary_key == rel.parent.get_db_column(rel.ref),
                left=True)
        else:
            where_col = rel.parent.primary_key
            xref = dict()
            for fk in rel.ref.foreign_keys:
                xref[fk.column.table.name] = rel.ref.c[fk.parent.name]
            col1 = xref[get_table_name(where_col.table)]
            from_item = FromItem(where_col.table, onclause=where_col == col1, left=True)

        query = select(columns=self.col_list(),
                       from_obj=self.from_obj(from_item),
                       whereclause=where_col == resource_id)
        query = self.group_query(query)
        if rel.cardinality in (ONE_TO_MANY, MANY_TO_MANY):
            query = self.sort_query(args, query)

        query = self.filter_query(query, filter_by)
        query = self.protect_query(query)
        query = query.distinct()

        if paginate and args.limit is not None:
            query = query.offset(args.offset).limit(args.limit)

        return query

    def included(self, rel, id_list):

        if rel.cardinality == ONE_TO_ONE:
            where_col = rel.model.primary_key
            query = select(columns=[*self.col_list(), where_col.label('parent_id')],
                           from_obj=self.from_obj(
                               FromItem(rel.model.primary_key.table,
                                        onclause=rel.model.primary_key == rel.parent.primary_key,
                                        left=True)))

        elif rel.cardinality == ONE_TO_MANY:
            where_col = rel.model.get_db_column(rel.ref)
            query = select(columns=[*self.col_list(), where_col.label('parent_id')],
                           from_obj=self.from_obj())

        elif rel.cardinality == MANY_TO_ONE:
            where_col = rel.parent.get_db_column(rel.ref)
            query = select(columns=[*self.col_list(), where_col.label('parent_id')],
                           from_obj=self.from_obj(
                               FromItem(rel.model.primary_key.table,
                                        onclause=rel.model.primary_key == where_col,
                                        left=True)))
        else:
            xref = dict()
            for fk in rel.ref.foreign_keys:
                xref[fk.column.table.name] = rel.ref.c[fk.parent.name]
            where_col = rel.parent.primary_key
            col1 = xref[get_table_name(where_col.table)]
            col2 = xref[get_table_name(rel.model.primary_key.table)]
            query = select(columns=[*self.col_list(), where_col.label('parent_id')],
                           from_obj=self.from_obj(
                               FromItem(rel.ref,
                                        onclause=col2 == rel.model.primary_key,
                                        left=True),
                               FromItem(where_col.table,
                                        onclause=where_col == col1,
                                        left=True)))

        query = self.group_query(query, where_col)
        query = self.protect_query(query)
        return (query.where(where_col.in_(x))
                for x in (id_list[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(id_list), SQL_PARAM_LIMIT)))
