***************
Defining Models
***************

.. currentmodule:: jsonapi.model

In this section we explore resource model definition in more detail.

To define a resource model, first declare a class that inherits from :class:`Model`
and set the :attr:`from_ <Model.from_>` attribute to an SQLAlchemy ``Table`` object::

    from jsonapi.model import Model
    from jsonapi.tests.db import users_t

    UserModel(Model):
        from_ = users_t

By default, the primary key column is mapped to the reserved ``id`` field.

.. note::

    Mapped tables must have single column primary keys.
    Composite primary key columns are not supported.

No additional attributes are required.

By default, the ``type`` of the resource is generated automatically from the model class name.
If you wish to override it, you can set it using the :attr:`type_ <Model.type_>` attribute::

        UserModel(Model):
            type_ = 'users'
            from_ = users_t

The :attr:`fields <Model.fields>` attribute can be used to define the set of attributes and
relationships for the resource. To define attributes that map directly to table columns of the
same name, simply list their names as string literals::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t
        fields = 'email', 'created-on'

The fields ``email`` and ``created-on`` will be created and mapped to the database columns:
``users_t.c.email`` and ``users_t.c.created_on``, respectively.

Custom Fields
=============

If you wish to map a field to a column of a different name, do so in the SQLAlchemy table
definition. For example, in the following example, "email_address" database column is mapped to
``users_t.c.email``::

    users_t = sa.Table(
        'users', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email_address', sa.Text, key='email',
                  unique=True, nullable=False),
        ...

The datatype of the field is detected automatically from the column datatype.
To override datatype auto-detection, you can explicitly set the datatype of the field
using the :class:`Field <jsonapi.fields.Field>` class::

    from jsonapi.fields import Field
    from jsonapi.datatypes import Date

    class UserModel(Model):
        from_ = users_t
        fields = ('email', 'name',
                  Field('created_on', field_type=Date))

The type of ``created_on`` field, which maps to a timestamp database column, is set to
:data:`Date` instead of :data:`DateTime`.

Multiple Tables
===============

A resource can be mapped to more than one database table::

    from jsonapi.tests.db import user_names_t

    class UserModel(Model):
        from_ = users_t, user_names_t

Fields are mapped to the columns of the joined tables. In the following example, the ``first``
and ``last`` columns of the ``user_names_t`` table are made available::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t, user_names_t
        fields = 'email', 'first', 'last'

If a left outer join or an explicit on clause is needed, a :class:`FromItem <jsonapi.db.FromItem>`
object can be passed in place of the table object. For example::

    from jsonapi import FromItem

    UserModel(Model):
        from_ = users_t, FromItem(user_names_t, left=True)

Derived Fields
==============

The :class:`Derived <jsonapi.fields.Derived>` class can be used to define derived fields::

    from jsonapi.fields import Derived

    class UserModel(Model):
            from_ = users_t, user_names_t
            fields = 'email', Derived('name', lambda c: c.first + ' ' + c.last)

The second argument takes a function that accepts an SQLAlchemy ``ImmutableColumnCollection``
representing the join result of the mapped tables listed in the ``from_`` attribute.
The function must return a valid column expression (including function calls)::

    Derived('age', lambda c: func.extract('year',
                                 func.age(c.birthday)), Integer))


Relationships
=============

The :class:`Relationship <jsonapi.fields.Relationship>` class can be used to define
relationships between resource models::

    from jsonapi import ONE_TO_MANY, MANY_TO_ONE
    from jsonapi.tests.db import articles_t

    class UserModel(Model):
        from_ = users_t, user_names_t
        fields = ('email',
                  Derived('name', lambda c: c.first + ' ' + c.last)
                  Relationship('articles', 'ArticleModel',
                               ONE_TO_MANY, 'author_id'))

    class ArticleModel(Model):
        from_ = articles_t
        fields = ('title', 'body', 'created_on',
                  Relationship('author', 'UserModel',
                               MANY_TO_ONE, 'author_id'))

In this example, a ``user`` can author multiple ``article``s, and an ``article``
is authored by one ``user``. This relationship is represented by two
:class:`Relationship <jsonapi.fields.Relationship>` objects, each defined in it's respective model.

The first argument to :class:`Relationship <jsonapi.fields.Relationship>` is the name
of the field. The second arguments is the target model class name. The third argument is
cardinality of the relationship.

The fourth argument depends on the cardinality of the relationship.

    - For ``ONE_TO_ONE`` relationships, no argument is required.
    - For ``ONE_TO_MANY`` and ``MANY_TO_ONE`` relationships, the argument must be a string
      representing the name of the column of the (non-composite) foreign key that is not the
      primary key of either related models.
    - For ``MANY_TO_MANY`` relationships, the argument is a 2-tuple representing the primary key
      of the join table, where the first must be part of the foreign key referencing the model's
      primary key (as opposed to the related model's primary key)

::

    article_keywords_t = sa.Table(
        'article_keywords', metadata,
        sa.Column('article_id', sa.Integer,
                  sa.ForeignKey('articles.id'),
                  nullable=False, index=True),
        sa.Column('keyword_id', sa.Integer,
                  sa.ForeignKey('keywords.id'),
                  nullable=False, index=True),
        sa.PrimaryKeyConstraint('article_id', 'keyword_id'))

    Relationship('keywords', 'KeywordModel',
                 MANY_TO_MANY, ('article_id', 'keyword_id'))

Aggregate Fields
================

The :class:`Aggregate <jsonapi.fields.Aggregate>` class can be used to define fields
that map to aggregate functions::

    class UserModel(Model):
        from_ = users_t

        fields = ('email', 'name', 'created_on',
                  Relationship('articles', 'ArticleModel',
                               ONE_TO_MANY, 'articles_author_id_fkey'),
                  Aggregate('article_count', 'articles', sa.func.count))

.. note::

    The second argument to ``Aggregate`` must match a name of a ``Relationship``
    field defined in the same model, as shown above.
