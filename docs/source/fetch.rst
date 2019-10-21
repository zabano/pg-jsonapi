#############
Fetching Data
#############

.. include:: warning.rst

For a given model instance, three methods are available for fetching resource data. All three methods expect a
dictionary of options as the first argument. These options represent the request query string parameters.

**************
Single Objects
**************

To fetch a single resource object, call the :meth:`Model.get_object` method, supplying the object id as the second
argument::

    >>> await UserModel().get_object({}, 1)
    {
        'data': {
            'id': '1',
            'type': 'user',
            'attributes': {
                'email': 'dianagraham@fisher.com',
                'first': 'Robert',
                'last': 'Camacho',
                'createdOn': '2019-05-18T11:49:43Z',
                'status': 'active',
                'name': 'Robert Camacho'}
        }
    }


The generated SQL query may look like this:

.. code-block:: postgresql

    SELECT users.id AS id,
           users.email AS email,
           user_names.first AS first,
           user_names.last AS last,
           users.created_on AS created_on,
           users.status AS status,
           user_names.first || ' ' || public.user_names.last AS name
    FROM public.users
    JOIN public.user_names ON public.users.id = public.user_names.user_id
    WHERE public.users.id = 1

***********
Collections
***********

To fetch a collection of objects, call the :meth:`Model.get_collection` method::

    >>> await UserModel().get_collection({})
    {'data': [
        {
            'id': '1',
            'type': 'user',
            'attributes': {
                'email': 'dianagraham@fisher.com',
                'first': 'Robert',
                'last': 'Camacho',
                'createdOn': '2019-05-18T11:49:43Z',
                'status': 'active',
                'name': 'Robert Camacho'
            }
        },
        ...
    ]}


The generated SQL query may look like this:

.. code-block:: postgresql

    SELECT users.id AS id,
           users.email AS email,
           user_names.first AS first,
           user_names.last AS last,
           users.created_on AS created_on,
           users.status AS status,
           user_names.first || ' ' || user_names.last AS name
    FROM users
    JOIN user_names ON users.id = user_names.user_id

***************
Related Objects
***************

To fetch related resource objects, call the :meth:`Model.get_related` method, supplying the object id and the
relation name as the second and third arguments::

    >>> await UserModel().get_related({}, 276, 'bio')
    {
        'data': {
            'id': '276',
            'type': 'user-bio',
            'attributes': {
                'summary': '...',
                'birthday': '2000-04-15',
                'age': 19
            }
        }
    }


The generated SQL query may look like this:

.. code-block:: postgresql

    SELECT _bio__user_bios_t.user_id AS id,
           _bio__user_bios_t.summary AS summary,
           _bio__user_bios_t.birthday AS birthday,
           EXTRACT(year FROM age(_bio__user_bios_t.birthday)) AS age
    FROM user_bios AS _bio__user_bios_t
    WHERE _bio__user_bios_t.user_id = :user_id_1

.. note::

    When fetching related (or included) object, table aliases are used.

****************
Sparse Fieldsets
****************

By default, only non-aggregate attribute fields are included in the response.
Aggregate fields must be requested explicitly and relationship fields are included when related resources are
requested using the ``include`` request parameter (see :ref:`include`).

To include specific attributes in the response, pass a comma separated list of field names using the appropriate
``fields[TYPE]`` option, where ``TYPE`` is the ``type`` of the resource model::

    >>> await UserModel().get_object({
    >>>     'fields[user]': 'name,email,created-on'
    >>> }, 1)
    {
        'data': {
            'id': '1',
            'type': 'user',
            'attributes': {
                'email': 'dianagraham@fisher.com',
                'createdOn': '2019-05-18T11:49:43Z',
                'name': 'Robert Camacho'}
        }
    }

You can pass an option for different resource types included in the response.
For an example, see :ref:`this <example_1>`.

.. _include:

******************************
Inclusion of Related Resources
******************************

To include related resources pass a comma separated list of relationship field names using the ``include``
option::

    >>> await UserModel().get_object({
    >>>     'include': 'bio',
    >>>     'fields[user]': 'name,email'}, 1)
    {
        'data': {
            'id': '1',
            'type': 'user',
            'attributes': {
                'email': 'dianagraham@fisher.com',
                'name': 'Robert Camacho'},
            'relationships': {
                'bio': None
            }
        }
    }

.. _example_1:

This user has no bio record, as indicated by the ``None`` value of the ``bio`` relationship. In the case of a non-empty
``bio`` relationship, the value will be set to a resource identifier object and a corresponding resource object will
be listed in the ``included`` section of the response document::

    >>> await UserModel().get_object({
    >>>     'include': 'bio',
    >>>     'fields[user]': 'name,email',
    >>>     'fields[user-bio]': 'birthday,age'}, 276)
    {
        'data': {
            'id': '276',
            'type': 'user',
            'attributes': {
                'email': 'dbarnes@yahoo.com',
                'name': 'Bryce Price'
            },
            'relationships': {
                'bio': {
                    'id': '276',
                    'type': 'user-bio'
                }
            }
        },
        'included': [
            {
                'id': '276',
                'type': 'user-bio',
                'attributes': {
                    'birthday': '2000-04-15',
                    'age': 19
                }
            }
        ]
    }

You can use dot notation to include nested relationships::

    >>> await UserModel().get_object({
    >>>     'include': 'articles.comments.replies,'
    >>>     'articles.keywords,articles.author,articles.publisher,'
    >>>     'bio'})

There is no limit on how many relationships can be included or nested.

*******
Sorting
*******

To sort a collection of resource objects, pass on the names of fields to order by as a comma separated list using the
``sort`` request parameter. You can use "+" or "-" prefix to indicate the sorting direction for each filed: ascending
or descending, respectively. No prefix implies ascending order.

For example, the following returns a collection of ``user`` objects sorted by the ``created-on`` field in descending
order::

     >>> await UserModel().get_collection({'sort': '-created-on'})

To sort the collection of followers of a specific ``user`` by last name first, and then by first name::

     >>> await UserModel().get_related({
     >>>     'sort': 'last,first'
     >>> }, 1, 'followers')

Collections can be sorted by aggregate fields::

    >>> await UserModel().get_collection({'sort': '-follower-count'})

Sorting by a relationship field, will sort by the related resource ``id`` field.
The following calls have identical effect::

    >>> await ArticleModel().get_collection({'sort': 'author'})
    >>> await ArticleModel().get_collection({'sort': 'author.id'})

You can use dot notation to specify a different attribute. To sort articles by the author name::

    >>> await ArticleModel().get_collection({'sort': 'author.name'})

Currently, dot notation can only be used to reference attribute fields of a relationship (one level of descent).

**********
Pagination
**********

To limit the number of objects returned in the ``data`` section of the response document, you can pass on the number
as the value of the ``page[size]`` option::

    >>> await UserModel().get_collection({
    >>>     'page[size]': 10,
    >>>     'sort': '-created-on'
    >>> })

The above call will return the 10 most recent ``user`` accounts.

To return the next batch, you can set the ``page[number]`` option to the appropriate value (defaults to 1)::

    >>> await UserModel().get_collection({
    >>>     'page[size]': 10,
    >>>     'page[number]': 2,
    >>>     'sort': '-created-on'
    >>> })

.. note::

    If ``page[number]`` parameter is set without providing ``page[size]``, an exception will be raised.

When pagination options are set, the ``total`` number of objects is provided in the ``meta`` section of the response
document::

    >>> await UserModel().get_collection({'page[size]': 10})
    {
        'data': [...],
        'meta': {
            'total': 1000
        }
    }

*********
Filtering
*********

The ``filter[SPEC]`` option can be used to filter a collection of objects (or related objects).

In the simplest form, ``SPEC`` can be the name of any field in the model.
This filter would include all objects where the field has a value equal to that supplied by the filter.
The value is parsed based on the datatype of the field.

For example, the following returns a list of active user accounts::

    >>> await UserModel().get_collection({
    >>>     'filter[status]': 'active'
    >>> })

By default, the filter will use the equality operator. To specify a different operator, you can append a colin and
the operator symbol to the name of the field. For example, to return all accounts created since September of 2019::

    >>> await UserModel().get_collection({
    >>>     'filter[created-on:gt]': '2019-09'
    >>> })

The supported operators (and their symbols) and value formats depends of the field's datatype.
For more details see :module:``jsonapi.datatypes``.

You can combine multiple filters, which will be AND-ed together::

    >>> await UserModel().get_collection({
    >>>     'filter[status:eq]': 'active',
    >>>     'filter[created-on:gt]': '2019-09'
    >>> })

Some datatypes accept comma-separated values. To fetch a specific list of users::

    >>> await UserModel().get_collection({
    >>>     'filter[id]': '1,2,3,6,8,9,10,11,12'
    >>> })

Ranges are also supported. The following is equivalent to the example above::

     >>> await UserModel().get_collection({'filter[id]': '<=3,6,>=8,12'})
     >>> await UserModel().get_collection({'filter[id]': '<4,6,>7,<13'})

Ranges are also supported by the date and time datatypes. To return all accounts created in September of 2019::

     >>> await UserModel().get_collection({
     >>>    'filter[created-on]': '>2019-09,<2019-10'
     >>> })

When filtering by a relationship fields, the objects are filtered by the ``id`` field related resource model. The
following calls are equivalent::

     >>> await ArticleModel().get_collection({'filter[author]': '1,2,3'})
     >>> await ArticleModel().get_collection({'filter[author.id]': '1,2,3'})

You can also filter by an attribute of a related resource model::

    >>> await ArticleModel().get_collection({'filter[author.status]': 'active'})

The reserved literals ``none``, ``null``, or ``na`` to filter empty relationships. The values are case-insensitive::

    >>> await ArticleModel().get_collection({'filter[author:eq]': 'none'})
    >>> await ArticleModel().get_collection({'filter[author:ne]': 'none'})

Currently, dot notation can only be used to reference attribute fields of a relationship (one level of descent).
