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

First we use SQLAlchemy to describe the database tables::

    import datetime as dt
    import sqlalchemy as sa

    metadata = sa.MetaData()

    PASSWORD_HASH_LENGTH = 128

    users_t = sa.Table(
        'users', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.Text, unique=True, nullable=False),
        sa.Column('created_on', sa.DateTime, nullable=False,
                  default=dt.datetime.utcnow),
        sa.Column('password', sa.String(PASSWORD_HASH_LENGTH),
                  nullable=False))

    user_names_t = sa.Table(
        'user_names', metadata,
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'),
                  primary_key=True, autoincrement=False),
        sa.Column('title', sa.Text),
        sa.Column('first', sa.Text, nullable=False),
        sa.Column('middle', sa.Text),
        sa.Column('last', sa.Text, nullable=False),
        sa.Column('suffix', sa.Text),
        sa.Column('nickname', sa.Text))

Now we define the model::

    from jsonapi.model import Model
    from jsonapi.fields import Derived


    class UserModel(Model):
        from_ = users_t, user_names_t
        fields = ('email', 'first', 'last', 'created_on'
                  Derived('name', lambda rec: rec.first + ' ' + rec.last))

.. note::

    There is no need to define an ``id`` field.
    The primary key of the mapped table is automatically assigned to the ``id`` field, regardless of
    what the column is called. Composite primary keys are not allowed in mapped columns (with the
     exception of join tables in many to many relationships, as discussed later). Also note that
     you can define fields for a subset of the available database columns. In the example above,
     we chose not to expose the "password" column, for example.

Now we are ready to implement the API calls.
In this tutorial we will be using the ``Quart`` web framework for demonstration purposes::

    import asyncio
    import uvloop
    from quart import Quart, jsonify, request
    from asyncpgsa import pg
    from jsonapi.model import MIME_TYPE

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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
        return jsonify(await UserModel().get_collection(request.args))

    @app.route('/users/<int:user_id>')
    async def user(user_id):
        return jsonify(await UserModel().get_resource(request.args, user_id))

    if __name__ == "__main__":
        app.run(host="localhost", port=8080, loop=asyncio.get_event_loop())

Example 1::

    GET http://localhost/users/
        ?fields[user]=created-on,name,email
        &sort=-created-on
        &page[size]=10

::

    HTTP/1.1 200
    content-type: application/vnd.api+json
    ...

::

    {
      "data": [
        {
          "attributes": {
            "createdOn": "2019-10-03T16:27:01Z",
            "email": "dana58@wall.org",
            "name": "Tristan Nguyen"
          },
          "id": "888",
          "type": "user"
        },
        {
          "attributes": {
            "createdOn": "2019-10-03T11:18:34Z",
            "email": "gilbertjacob@yahoo.com",
            "name": "Christian Bennett"
          },
          "id": "270",
          "type": "user"
        },
        ...
      ],
      "meta": {
        "total": 1000
      }
    }

Example 2::

    GET http://localhost/users/1
        ?fields[user]=email,name

::

    HTTP/1.1 200
    content-type: application/vnd.api+json
    ...

::

    {
      "data": {
        "attributes": {
          "email": "dianagraham@fisher.com",
          "name": "Robert Camacho"
        },
        "id": "1",
        "type": "user"
      }
    }


Next Steps
----------

In the following sections we will guide you through the different features available.