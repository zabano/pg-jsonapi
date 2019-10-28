###############
Defining Models
###############

.. include:: warning.rst

.. currentmodule:: jsonapi.model

In this section we explore resource model definition in more detail.

To define a resource model, first declare a class that inherits from :class:`Model` and set the :attr:`from_ <Model
.from_>` attribute to an SQLAlchemy ``Table`` object::

    from jsonapi.model import Model
    from jsonapi.tests.db import users_t

    UserModel(Model):
        from_ = users_t

By default, the primary key column is mapped to the reserved ``id`` field.

.. note::

    Mapped tables must have single column primary keys.
    Composite primary key columns are not supported.

No additional attributes are required.

By default, the ``type`` of the resource is generated automatically from the model class name. If you wish to
override it, you can set it using the :attr:`type_ <Model.type_>` attribute::

        UserModel(Model):
            type_ = 'users'
            from_ = users_t

The :attr:`fields <Model.fields>` attribute can be used to define the set of attributes and relationships for the
resource. To define attributes that map directly to table columns of the same name, simply list their names as string
literals::

    class UserModel(Model):
        type_ = 'user'
        from_ = users_t
        fields = 'email', 'created_on'

The fields ``email`` and ``created_on`` will be created and mapped to the database columns: ``users_t.c.email`` and
``users_t.c.created_on``, respectively.

*************
Custom Fields
*************

The datatype of the field is determined automatically from the datatype of the database column it maps to. To
override datatype auto-detection, you can explicitly set the datatype using the :class:`Field <jsonapi.fields.Field>`
class::

    from jsonapi.fields import Field
    from jsonapi.datatypes import Date

    class UserModel(Model):
        from_ = users_t
        fields = ('email', 'status', Field('created_on', field_type=Date))

The type of ``created_on`` field, which maps to a timestamp database column, is set to :data:`Date` instead of
:data:`DateTime`.

To define a field that maps to a number of columns (a column expression)::

    class UserModel(Model):
            from_ = users_t, user_names_t
            fields = 'email', Field('name', lambda c: c.first + ' ' + c.last)

The second argument takes a function that accepts an SQLAlchemy ``ImmutableColumnCollection`` representing the join
result of the mapped tables listed in the ``from_`` attribute. The function must return a valid column expression
(including function calls)::

    Field('age', lambda c: func.extract('year', func.age(c.birthday)), Integer))


If you wish to map a field to a database column of a different name::

    class UserModel(Model):
        from_ = users_t
        fields = 'status', Field('email_address', lambda c: c.email)

You can also pass an SQLAlchemy ``Column`` explicitly. This is useful when mapping to multiple tables that share the
same column names (see :ref:`multiple_tables`)::

    class UserModel(Model):
        from_ = users_t
        Field('email-address', users_t.c.email)

.. _multiple_tables:

***************
Multiple Tables
***************

A resource model can be mapped to more than one database table::

    from jsonapi.tests.db import user_names_t

    class UserModel(Model):
        from_ = users_t, user_names_t

In the following example, we define three fields. One maps to ``users_t.c.email`` column, and two map to
``user_names_t.c.first`` and ``user_names_t.c.last`` columns::

    class UserModel(Model):
        type_ = 'user'
        from_ = users_t, user_names_t
        fields = 'email', 'first', 'last'

If a left outer join or an explicit on clause is needed, a :class:`FromItem <jsonapi.db.FromItem>` object can be
passed in place of the table object. For example::

    from jsonapi import FromItem

    UserModel(Model):
        from_ = users_t, FromItem(user_names_t, left=True)


*************
Relationships
*************

The :class:`Relationship <jsonapi.fields.Relationship>` class can be used to define relationships between resource
models::

    from jsonapi import ONE_TO_MANY, MANY_TO_ONE
    from jsonapi.tests.db import articles_t

    class UserModel(Model):
        from_ = users_t, user_names_t
        fields = ('email',
                  Derived('name', lambda c: c.first + ' ' + c.last)
                  Relationship('articles', 'ArticleModel',
                               ONE_TO_MANY, articles_t.c.author_id))

    class ArticleModel(Model):
        from_ = articles_t
        fields = ('title', 'body', 'created_on',
                  Relationship('author', 'UserModel',
                               MANY_TO_ONE, articles_t.c.author_id))

In this example, a ``user`` can author multiple ``article`` s, and an ``article`` is authored by one ``user``. This
relationship is represented by two :class:`Relationship <jsonapi.fields.Relationship>` objects, each defined in it's
respective model.

The first argument to :class:`Relationship <jsonapi.fields.Relationship>` is the name of the field. The second
arguments is the target model class name. The third argument is cardinality of the relationship.

The fourth and possibly fifth arguments depend on the cardinality of the relationship.
Both arguments, if provided must be SQLAlchemy ``Column`` objects that are part of a foreign key and are not a
primary key of any model.

    - For ``ONE_TO_ONE`` relationships, no argument is required in most cases.
      The only exception is when the foreign key of the relationship lives in a standalone one-to-one join table.
    - For ``ONE_TO_MANY`` and ``MANY_TO_ONE`` relationships, one argument is required.
    - For ``MANY_TO_MANY`` relationships, two arguments are required and the second must be the one referencing the
      primary key of the related resource model

.. code-block::
    :emphasize-lines: 14-16

    article_keywords_t = sa.Table(
        'article_keywords', metadata,
        sa.Column('article_id', sa.Integer,
                  sa.ForeignKey('articles.id'),
                  nullable=False, index=True),
        sa.Column('keyword_id', sa.Integer,
                  sa.ForeignKey('keywords.id'),
                  nullable=False, index=True),
        sa.PrimaryKeyConstraint('article_id', 'keyword_id'))

    class ArticleModel(Model):
        from_ = articles_t
        fields = ('title', 'body', ...
                  Relationship('keywords', 'KeywordModel', MANY_TO_MANY,
                               article_keywords_t.c.article_id,
                               article_keywords_t.c.keyword_id))

****************
Aggregate Fields
****************

The :class:`Aggregate <jsonapi.fields.Aggregate>` class can be used to define fields that map to aggregate functions::

    class UserModel(Model):
        from_ = users_t

        fields = ('email', 'name', 'created_on',
                  Relationship('articles', 'ArticleModel',
                               ONE_TO_MANY, articles_t.c.author_id),
                  Aggregate('article_count', 'articles', sa.func.count))

.. note::

    The second argument to ``Aggregate`` must match a name of a ``Relationship`` field defined in the same model, as
    shown above.
