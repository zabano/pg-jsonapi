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

Data Types
==========

.. automodule:: jsonapi.datatypes

.. note::

    Field data types are detected automatically. Use one of the following data types when
    an explicit type is required.

.. autodata:: jsonapi.datatypes.Bool
    :annotation: bool types (sa.Boolean)

.. autodata:: jsonapi.datatypes.Integer
    :annotation: integer types (sa.Integer, sa.SmallInteger, sa.BigInteger)

.. autodata:: jsonapi.datatypes.Float
    :annotation: floating point or fixed precision numbers (sa.Float, sa.Numeric)

.. autodata:: jsonapi.datatypes.String
    :annotation: string and character types (sa.String, sa.Text, sa.Enum, sa.Unicode, sa.UnicodeText)

.. autodata:: jsonapi.datatypes.Date
    :annotation: date values (sa.Date)

.. autodata:: jsonapi.datatypes.DateTime
    :annotation: timestamps without time zone (sa.DateTime)

.. autodata:: jsonapi.datatypes.Time
    :annotation: time values (sa.Time)

Fields
======

.. automodule:: jsonapi.fields

Simple Fields
-------------

.. autoclass:: jsonapi.fields.Field

    .. automethod:: __init__


Derived Fields
--------------

.. autoclass:: jsonapi.fields.Derived

    .. automethod:: __init__

Aggregate Fields
----------------

.. class:: jsonapi.fields.Aggregate(name, expr, func, field_type=Integer)

    .. automethod:: __init__(name, expr, func, field_type=Integer)

Relationships
-------------

.. autoclass:: jsonapi.fields.Relationship

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