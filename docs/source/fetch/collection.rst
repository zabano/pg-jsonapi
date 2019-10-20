##########################
Fetching Data: Collections
##########################

.. currentmodule:: jsonapi.model

.. include:: shared.rst

To fetch a single resource object, call the :meth:`Model.get_object` method, supplying the
object id as the second argument::

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


Sparse Fieldsets
================

By default, all non aggregate attribute fields are included in the response.
Aggregate fields must be requested explicitly.

In addition, relationship fields are not included. They are only included when related resources
are requested using the ``include`` request parameter (see the next section).

To include specific attributes in the response, simply pass on the appropriate ``fields[TYPE]``
request parameter::

    >>> await UserModel().get_object({'fields[user]': 'name,email,created-on'}, 1)
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



Inclusion of Related Resources
==============================

As mentioned above, to include related resources pass on the ``include`` request parameter::

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

This user has no bio record, as indicated by the ``None`` value of the ``bio`` relationship.
When related resources exist, they will be returned as part of the ``included`` section of the
response document::

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


Sorting
=======

Pagination
==========

Filtering
=========



