#########
Searching
#########

.. include:: warning.rst

.. currentmodule:: jsonapi.model

A model can be made searchable by setting the :attr:`search <Model.search>` attribute of the model to an SQLAlchemy
``Table`` object representing a fulltext search index table. The table must consist of a primary key column that
references the model's primary key, and an indexed ``TSVECTOR`` column.

For an example, to make our ``UserModel`` searchable we define a text search table as follows::

    from sqlalchemy.dialects.postgresql import TSVECTOR

    users_ts = sa.Table(
        'users_ts', metadata,
        sa.Column('user_id', sa.Integer,
                  sa.ForeignKey('users.id'),
                  primary_key=True),
        sa.Column('tsvector', TSVECTOR,
                  index=True, nullable=False))

And then we redefine the model as follows:

.. code-block:: python
    :emphasize-lines: 4

    class UserModel(Model):
        from_ = users_t, user_names_t
        fields = (...)
        search = users_ts

As an example, the following SQL can be used to populate the index table:

.. code-block:: postgresql

    INSERT INTO users_ts (user_id, tsvector)
    SELECT users.id,
           setweight(to_tsvector(users.email), 'A') ||
           setweight(to_tsvector(user_names.last), 'B') ||
           setweight(to_tsvector(user_names.first), 'B')
    FROM users
             JOIN user_names ON users.id = user_names.user_id
    ORDER BY users.id;

**************
A Single Model
**************

To search a single resource model, simply pass the fulltext search term as the ``search`` argument of
:meth:`Model.get_collection` or :meth:`Model.get_related` for to-many relationships::

    >>> await UserModel().get_collection({}, search='John')
    >>> await UserModel().get_related(1, 'followers', search='John')

The result of a search query is always sorted by the search result ranking, and any ``sort`` option provided will be
ignored.

Filtering and searching are not compatible, and cannot be used simultaneously. Doing so will raise an exception::

    >>> await UserModel().get_collection({'filter[id]': '1,2,3'}, search='John')
    Traceback (most recent call last):
    ...
    jsonapi.exc.APIError: [UserModel] cannot filter and search at the same time

***************
Multiple Models
***************

Use the :func:`search` function to search multiple resource models at once and return a heterogeneous collection of
objects::

    >>> from jsonapi.model import search
    >>> search({}, 'John', UserModel, ArticleModel)

The first argument is a dictionary of options representing the request parameters.
The second argument is PostgreSQL full text search query string.

Any additional arguments are expected to be model classes or instances. At least two unique models are expected.

Pagination is supported, while filtering and sorting are not.
To include related resources for a model type, provide an appropriate ``include[TYPE]`` option. A simple ``include``
option will be ignored::

    >>> search({'include[user]': 'bio',
    >>>         'include[article]': 'keywords,author.bio,publisher.bio',
    >>>         'fields[user]': 'name,email',
    >>>         'fields[user-bio]': 'birthday,age',
    >>>         'fields[article]': 'title'},
    >>>         'John', UserModel, ArticleModel)
