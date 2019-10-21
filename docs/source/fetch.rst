#############
Fetching Data
#############

.. include:: warning.rst

For a given model instance, three methods are available for fetching resource
data. All three methods expect a dictionary of options as the first argument.
These options represent the request query string parameters.

**************
Single Objects
**************

To fetch a single resource object, call the :meth:`Model.get_object` method,
supplying the object id as the second argument::

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

To fetch related resource objects, call the :meth:`Model.get_related` method,
supplying the object id and the relation name as the second and third
arguments::

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

By default, all non aggregate attribute fields are included in the response.
Aggregate fields must be requested explicitly.

In addition, relationship fields are not included. They are only included
when related resources are requested using the ``include`` request parameter
(see :ref:`include`).

To include specific attributes in the response, simply pass on the
appropriate ``fields[TYPE]`` option, where ``TYPE`` is the ``type`` of the
resource::

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

You can pass an option for each resource type included in the response.
For an example, see :ref:`this <example_1>`.

.. _include:

******************************
Inclusion of Related Resources
******************************

As mentioned above, to include related resources pass on the ``include``
request parameter::

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

This user has no bio record, as indicated by the ``None`` value of the
``bio`` relationship. When related resources exist, they will be returned as
part of the ``included`` section of the response document::

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

*******
Sorting
*******

To sort a collection of resource objects, pass on the names of fields to
order by as a comma separated list using the ``sort`` request parameter.
You can use "+" or "-" prefix to indicate the sorting direction for each filed:
ascending or descending, respectively. No prefix implies ascending order.

For example, the following returns a collection of ``user``
objects sorted by the ``created-on`` field in descending order::

     >>> await UserModel().get_collection({'sort': '-created-on'})

To sort the collection of followers of a specific ``user`` by last name and
then first name::

     >>> await UserModel().get_related({
     >>>     'sort': 'last,first'
     >>> }, 1, 'followers')

Collections can be sorted using aggregate fields::

    >>> await UserModel().get_collection({'sort': '-follower-count'})

Sorting by a relationship field, will sort by the related resource ``id`` field.
The following calls have identical effect::

    >>> await ArticleModel().get_collection({'sort': 'author'})
    >>> await ArticleModel().get_collection({'sort': 'author.id'})

You can use dot notation to specify a different attribute field.
To sort articles by author name::

    >>> await ArticleModel().get_collection({'sort': 'author.name'})

Currently, dot notation can only be used to reference attribute fields of a
relationship (one level of descent).

**********
Pagination
**********

To limit the number of objects returned in the ``data`` section of the
response document, you can pass on the number as the value of the
``page[size]`` option::

    >>> await UserModel().get_collection({
    >>>     'page[size]': 10,
    >>>     'sort': '-created-on'
    >>> })

The above call will return the 10 most recent ``user`` accounts.
To return the next batch, you can set the ``page[number]`` option to the
appropriate value (defaults to 1)::

    >>> await UserModel().get_collection({
    >>>     'page[size]': 10,
    >>>     'page[number]': 2,
    >>>     'sort': '-created-on'
    >>> })

.. note::

    If ``page[number]`` parameter is set without providing ``page[size]``, an
    exception will be raised.

When pagination options are set, the ``total`` number of objects is provided in
the ``meta`` section of the response document::

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
