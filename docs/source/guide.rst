==========
User Guide
==========

.. warning:: Under Development

.. currentmodule:: jsonapi.model

In this section we explore resource model definition in more detail.

Resource Models
===============

To define a resource model we declare a class that inherits from :class:`Model` and
set the :attr:`type_ <Model.type_>` attribute to a unique string value.
The :attr:`from_ <Model.from_>` attribute is used to specify the table to which to map the
model fields::

    import jsonapi as ja
    from jsonapi.tests.db import users_t

    UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t

By default, the primary key column is mapped to the reserved ``id`` field.

.. note::

    Composite primary key columns are not supported, except for join tables in many-to-many
    relationships.

No additional fields need to be defined. The :attr:`fields <Model.fields>` attribute can
be used to define the set of attributes and relationships for the resource. To define
attributes that map directly to table columns of the same name, simply list them::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t
        fields = 'email', 'name'

The fields ``email`` and ``name`` will be created and mapped to the database columns: ``users_t.c
.email`` and ``users_t.c.name``, respectively. The field types will be detected automatically as
well.

Custom Fields
=============

If you wish to map a field to a column of a different name, you can explicitly define the field
using the :class:`Field` class::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t
        fields = Field('email_address', users_t.c.email), 'name'

You can also override type auto-detection::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t
        fields = 'email', 'name', ja.Field('created_on', field_type=ja.Date)

The type of ``created_on`` field, which maps to a timestamp database column, is set to
:data:`Date` instead of :data:`DateTime`.

Mapping to Multiple Tables
==========================

A resource can be mapped to more than one database table::

    from jsonapi.tests.db import user_names_t

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t, user_names_t

The listed tables are joined together (using full inner join) when the data are fetched.
The columns of the joined tables are then available to map to specific fields::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t, user_names_t
        fields = 'email', 'first', 'last'

If a left outer join or an explicit on clause is needed, a :class:`FromItem <jsonapi.db.FromItem>`
object can be passed in place of the table object. For example::

    UserModel(ja.Model):
        type_ = 'users'
        from_ = users_t, FromItem(user_names_t, left=True)

Derived Fields
==============

There are two options for defining derived fields.

The first option is to use the :class:`Field` class::

    class UserModel(ja.Model):
        type_ = 'user'
        from_ = users_t, user_names_t
        fields = 'email', ja.Field('name', user_names_t.c.first + ' ' + user_names_t.c.last)

In this case, the ``name`` field value is directly provided by the select query.

The second option is to use the :class:`Derived` class which is a subclass
of :class:`Field`::

    class UserModel(ja.Model):
            type_ = 'user'
            from_ = users_t, user_names_t
            fields = 'email', ja.Derived('name',
                                         lambda rec: '{first} {last}.format(**rec)')

Here, the ``name`` is created during the serialization of the object.

Relationships
=============

The :class:`Relationship` class can be used to define relationships between
resource models::

    from jsonapi.tests.db import articles_t

    class UserModel(Model):
        type_ = 'user'
        from_ = users_t

        fields = ('email', 'name',
                  Relationship('articles', 'ArticleModel',
                               ja.ONE_TO_MANY, 'articles_author_id_fkey'))

    class ArticleModel(Model):
        type_ = 'article'
        from_ = articles_t
        fields = ('title', 'body', 'created_on',
                  Relationship('author', 'UserModel',
                               ja.MANY_TO_ONE, 'articles_author_id_fkey'))

In this example, a ``user`` can author multiple ``article``s, and an ``article`` is authored by one
``user``. This relationship is represented by two :class:`Relationship`
objects, each defined as a field in each of the models.

The first argument to :class:`Relationship` is the name of the field, as
expected. The other arguments are the target model name, the cardinality of the relationship, and
the name of the foreign key (as defined in the SQLAlchemy table description), in that order.

.. note::

    The foreign key must be specified explicitly. The reason it was not done automatically to avoid
    accidentally using the wrong foreign key in the future, if the table description is updated.

Aggregate Functions
===================

The :class:`Aggregate` class can be used to define fields that map to aggregate
functions::

    class UserModel(Model):
        type_ = 'user'
        from_ = users_t

        fields = ('email', 'name', 'created_on',
                  Relationship('articles', 'ArticleModel',
                               ONE_TO_MANY, 'articles_author_id_fkey'),
                  Aggregate('article_count',
                            sa.func.count(articles_t.c.id.distinct()),
                            FromItem(articles_t, left=True)))
