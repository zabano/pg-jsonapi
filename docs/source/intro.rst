============
Introduction
============

.. warning:: Under Development

**pg-jsonapi** is an asynchronous Python library for building `JSON API v1.0
<https://jsonapi.org/format/>`_  compliant calls using a very simple declarative syntax.

Only ``PostgreSQL`` is supported.
``PostgreSQL`` integration is powered by the
`asyncpgsa <https://asyncpgsa.readthedocs.io/en/latest/>`_ library.

`SQLAlchemy <https://www.sqlalchemy.org/>`_ core is also required for describing database objects.

Under the hood, the `marshmallow <https://marshmallow.readthedocs.io/en/stable/>`_ library is used
for object serialization. No previous knowledge of ``marshmallow`` is required.

The user can define models that map to ``SQLAlchemy`` tables. Each model represents a single
JSON API resource. Each resource has a unique type. A set of fields can be defined for each
resource. A field can be a simple attribute that maps directly to a database column,
or derived from multiple columns. The user may also define aggregate fields (ex. counts, max
values, etc.). Relationship fields can be used to define relationships between models.

The library supports the fetching of resource data, as well as fieldsets, sorting, filtering, and
inclusion of related resources.

Quick Start
===========

In this simple start up example, we will show how to create a resource model and use it to
implement two basic API calls.

First we use SQLAlchemy to describe a database table::

    import sqlalchemy as sa
    import datetime as dt

    metadata = sa.MetaData()

    PASSWORD_HASH_LENGTH = 128

    users_t = sa.Table('users', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.Text, unique=True, nullable=False),
        sa.Column('name', sa.Text),
        sa.Column('password', sa.String(PASSWORD_HASH_LENGTH),
                  nullable=False),
        sa.Column('created_on', sa.DateTime, nullable=False,
                   default=dt.datetime.utcnow))

Now we define the model::

    import jsonapi as ja

    class UserModel(ja.Model):
        type = 'user'
        tables = users_t
        fields = ('email', 'name', 'created_on')

.. note::

    There is no need to define an ``id`` field.
    The primary key of the mapped table is automatically assigned to the ``id`` field, regardless of
    what the column is called. Composite primary keys are not allowed, except for join tables (in
    many to many relationships). In addition, you can define fields for a subset of the available
    database columns.

Now we are ready to implement the API calls using ``Quart``::

    from quart import Quart
    from quart import jsonify
    from asyncpgsa import pg
    from jsonapi import MIME_TYPE

    app = Quart('jsonapi-test')
    app.config['JSONIFY_MIMETYPE'] = MIME_TYPE

    @app.before_first_request
    async def init():
        await pg.init(database='jsonapi',
                      user='jsonapi',
                      password='jsonapi',
                      min_size=5, max_size=10)

    @app.route('/users/')
    async def users():
        return jsonify(await UserModel().get_collection())

    @app.route('/users/<int:user_id>')
    async def user(user_id):
        return jsonify(await UserModel().get_resource(user_id))

Example output::

    GET http://localhost/users/

    HTTP/1.1 200
    content-type: application/vnd.api+json
    content-length: 246
    date: Wed, 04 Sep 2019 20:54:47 GMT
    server: hypercorn-h11

    {
      "data": [
        {
          "attributes": {
            "createdOn": "2019-08-27T19:02:31Z",
            "email": "john.smith@jsonapi.test",
            "name": "John Smith"
          },
          "id": "2",
          "type": "user"
        },
        {
          "attributes": {
            "createdOn": "2019-08-27T19:01:00Z",
            "email": "jane.doe@jsonapi.test",
            "name": "Jane Doe"
          },
          "id": "1",
          "type": "user"
        }
      ]
    }

    GET http://localhost/users/1

    HTTP/1.1 200
    content-type: application/vnd.api+json
    content-length: 126
    date: Wed, 04 Sep 2019 20:55:56 GMT
    server: hypercorn-h11

    {
      "data": {
        "attributes": {
          "createdOn": "2019-08-27T19:01:00Z",
          "email": "jane.doe@jsonapi.test",
          "name": "Jane Doe"
        },
        "id": "1",
        "type": "user"
      }
    }

Next Steps
----------

In the following sections we will guide you through the different features available.