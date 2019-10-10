from sqlalchemy.sql import and_, exists, func, select

from jsonapi.exc import APIError, ModelError
from jsonapi.fields import Aggregate, Field
from .table import FromClause, FromItem, MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE, \
    get_table_name, get_foreign_key_pair

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

    def col_list(self, *columns, **kwargs):

        col_list = [self.model.attributes['id'].expr.label('id')]
        col_list.extend(columns)

        group_by = bool(kwargs.get('group_by', False))
        field_type = (Field, Aggregate) if group_by else Field

        for name, field in self.model.attributes.items():
            if field.name != 'id' and isinstance(field, field_type) and field.expr is not None:
                col_list.append(field.expr.label(name))

        search = kwargs.get('search', None)
        if self.model.search is not None and search is not None:
            col_list.append(self.rank_column(search))

        return col_list

    def from_obj(self, *additional):
        from_clause = FromClause()
        from_clause.extend(self.model.from_clause)
        from_clause.extend(additional)
        for field in self.model.fields.values():
            if isinstance(field, Aggregate) and field.expr is not None:
                for from_item in field.from_items[self.model.name]:
                    from_clause.append(from_item)
        return from_clause()

    def rank_column(self, search):
        if self.model.search is not None and search is not None:
            return func.ts_rank_cd(
                self.model.search.c.tsvector, func.to_tsquery(search)).label('_ts_rank')

    ################################################################################################
    # query
    ################################################################################################

    def group_query(self, query, *columns, **kwargs):
        filter_by = kwargs.get('filter_by', None)
        if self.is_aggregate() or (filter_by is not None and len(filter_by.having) > 0):
            query = query.group_by(*self.col_list(*columns))
        return query

    @staticmethod
    def filter_query(query, filter_by):
        if not filter_by:
            return query
        if filter_by.where:
            query = query.where(and_(*filter_by.where))
        if filter_by.having:
            query = query.having(and_(*filter_by.having))
        if filter_by.distinct:
            query = query.distinct()
        return query

    def sort_query(self, args, query, search=None):
        if self.model.search is not None and search is not None:
            return query.order_by(self.rank_column(search).desc())
        order_by = list()
        for name, desc in args.sort.items():
            try:
                field = self.model.fields[name]
            except KeyError:
                raise APIError('column does not exist: {}'.format(name), self.model)
            else:
                if not field.is_relationship() and field.expr is not None:
                    order_by.append(getattr(field.expr, 'desc' if desc else 'asc')().nullslast())

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
                       columns=self.col_list(group_by=self.is_aggregate()),
                       whereclause=self.model.primary_key == resource_id)
        query = self.group_query(query)
        if self.model.access is not None:
            query = self.protect_query(query)
        return query

    def all(self, args, filter_by=None, paginate=True, count=False, search=None):
        search_t = self.model.search

        from_items = list()
        if filter_by:
            from_items.extend(filter_by.from_items)
            from_items.extend(filter_by.from_items_last)
        if search is not None:
            from_items.append(search_t)
        query = select(columns=self.col_list(search=search, group_by=self.is_aggregate()),
                       from_obj=self.from_obj(*from_items))

        query = self.group_query(query, filter_by=filter_by)
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
            where_col, ref_col = get_foreign_key_pair(rel.ref, rel.parent)
            from_item = FromItem(rel.ref, onclause=rel.model.primary_key == ref_col, left=True)

        query = select(columns=self.col_list(group_by=self.is_aggregate()),
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
            parent_col = rel.model.primary_key
            from_item = FromItem(rel.model.primary_key.table,
                                 onclause=rel.model.primary_key == rel.parent.primary_key,
                                 left=True)
            query = select(
                columns=self.col_list(parent_col.label('parent_id'),
                                      group_by=self.is_aggregate()),
                from_obj=self.from_obj(from_item))

        elif rel.cardinality == ONE_TO_MANY:
            parent_col = rel.model.get_db_column(rel.ref)
            query = select(
                columns=self.col_list(parent_col.label('parent_id'),
                                      group_by=self.is_aggregate()),
                from_obj=self.from_obj())

        elif rel.cardinality == MANY_TO_ONE:
            parent_col = rel.parent.primary_key
            from_item = FromItem(
                rel.parent.primary_key.table,
                onclause=rel.model.primary_key == rel.parent.get_db_column(rel.ref),
                left=True)
            query = select(
                columns=self.col_list(parent_col.label('parent_id'),
                                      group_by=self.is_aggregate()),
                from_obj=self.from_obj(from_item))

        else:
            xref = dict()
            for fk in rel.ref.foreign_keys:
                xref[fk.column.table.name] = rel.ref.c[fk.parent.name]
            parent_col = xref[get_table_name(rel.parent.primary_key.table)]
            model_col = xref[get_table_name(rel.model.primary_key.table)]
            query = select(
                columns=self.col_list(parent_col.label('parent_id'),
                                      group_by=self.is_aggregate()),
                from_obj=self.from_obj(FromItem(rel.ref,
                                                onclause=model_col == rel.model.primary_key,
                                                left=True)))

        query = self.group_query(query, parent_col)
        query = self.protect_query(query)
        return (query.where(parent_col.in_(x))
                for x in (id_list[i:i + SQL_PARAM_LIMIT]
                          for i in range(0, len(id_list), SQL_PARAM_LIMIT)))
