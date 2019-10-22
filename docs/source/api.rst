#############
API Reference
#############

.. include:: warning.rst

.. automodule:: jsonapi

******
Models
******

.. automodule:: jsonapi.model

.. autodata:: jsonapi.model.MIME_TYPE

.. autodata:: jsonapi.model.SEARCH_PAGE_SIZE

.. autoclass:: jsonapi.model.Model

    .. autoattribute:: type_
        :annotation:

        See :doc:`model` for more details.

    .. autoattribute:: from_
        :annotation:

        See :doc:`model` for more details.

    .. autoattribute:: fields
        :annotation:

        See :doc:`model` for more details.

    .. autoattribute:: access
        :annotation:

        See :doc:`access` for more details.

    .. autoattribute:: user
        :annotation:

        See :doc:`access` for more details.

    .. autoattribute:: search
        :annotation:

        See :doc:`ts` for more details.

    .. automethod:: get_object

        See :ref:`Fetching Data: Single Object <object>` for more details.

    .. automethod:: get_collection

        See :ref:`Fetching Data: Collections <collection>` for more details.

    .. automethod:: get_related

        See :ref:`Fetching Data: Related Objects <related>` for more details.

.. autofunction:: search

    See :doc:`ts` for more details.

**********
From Items
**********

.. autoclass:: jsonapi.db.table.FromItem

    .. automethod:: __init__

******
Fields
******

.. automodule:: jsonapi.fields

Basic Fields
============

.. autoclass:: jsonapi.fields.Field

    .. automethod:: __init__


Derived Fields
==============

.. autoclass:: jsonapi.fields.Derived

    .. automethod:: __init__

Aggregate Fields
================

.. class:: jsonapi.fields.Aggregate(name, expr, func, field_type=Integer)

    .. automethod:: __init__(name, expr, func, field_type=Integer)

Relationships
=============

.. autoclass:: jsonapi.fields.Relationship

    .. automethod:: __init__

Cardinality
-----------

.. autoclass:: jsonapi.db.table.Cardinality
