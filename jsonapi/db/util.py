def get_primary_key(table):
    """
    Get table primary key column.

    .. note::

        Assumes a simple (non-composite) key and returns the first column.

    :param table: SQLAlchemy Table object
    :return: the primary key column
    """
    return table.primary_key.columns.values()[0]
