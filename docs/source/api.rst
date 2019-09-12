=============
API Reference
=============

.. warning:: Under Development

.. automodule:: jsonapi

.. automodule:: jsonapi.model

Models
======

.. autoclass:: jsonapi.model.Model

    .. autoattribute:: type_
        :annotation:

    .. autoattribute:: from_
        :annotation:

    .. autoattribute:: fields
        :annotation:

    .. autoattribute:: search
        :annotation:


    .. automethod:: get_object
    .. automethod:: get_collection
    .. automethod:: get_related

Fields
======

Field Data Types
----------------

.. note::

    Field data types are detected automatically. Use one of the following data types when
    an explicit type is required.

.. autodata:: jsonapi.model.Bool
    :annotation: bool types (sa.Boolean)

.. autodata:: jsonapi.model.Integer
    :annotation: integer types (sa.Integer, sa.SmallInteger, sa.BigInteger)

.. autodata:: jsonapi.model.Float
    :annotation: floating point or fixed precision numbers (sa.Float, sa.Numeric)

.. autodata:: jsonapi.model.String
    :annotation: string and character types (sa.String, sa.Text, sa.Enum, sa.Unicode, sa.UnicodeText)

.. autodata:: jsonapi.model.Date
    :annotation: date values (sa.Date)

.. autodata:: jsonapi.model.DateTime
    :annotation: timestamps without time zone (sa.DateTime)

.. autodata:: jsonapi.model.Time
    :annotation: time values (sa.Time)

Simple Fields
-------------

.. autoclass:: jsonapi.model.Field

    .. automethod:: __init__


Derived Fields
--------------

.. autoclass:: jsonapi.model.Derived

    .. automethod:: __init__

Aggregate Fields
----------------

.. class:: jsonapi.model.Aggregate(name, expr, from_items, field_type=Integer)

    .. automethod:: __init__(name, expr, from_items, field_type=Integer)

Relationships
-------------

.. autoclass:: jsonapi.model.Relationship

    .. automethod:: __init__

Database
========

.. automodule:: jsonapi.db

Queries
-------

.. autoclass:: jsonapi.db.Query


From Clauses
------------

.. autoclass:: jsonapi.db.FromClause

    .. automethod:: __init__


From Items
----------

.. autoclass:: jsonapi.db.FromItem

    .. automethod:: __init__


Cardinality
-----------

.. autodata:: jsonapi.db.ONE_TO_ONE
.. autodata:: jsonapi.db.MANY_TO_ONE
.. autodata:: jsonapi.db.ONE_TO_MANY
.. autodata:: jsonapi.db.MANY_TO_MANY


Utility Functions
-----------------

.. autofunction:: jsonapi.db.get_primary_key