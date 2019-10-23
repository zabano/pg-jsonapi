#################
Protecting Models
#################

.. include:: warning.rst

.. currentmodule:: jsonapi.model

By default, models are not protected and all their objects are accessible (i.e. visible).

Protected models control access to their objects.
A protected model checks access for each object to be included in the response.
If access is not granted, the object is either silently excluded from the response or an appropriate exception is
raised, depending on the context.

A model can be protected by setting the :attr:`access <Model.access>` attribute of the model to an SQL function that
accepts two arguments: the ``id`` of the resource object and the current (logged-in) user id, and returns a boolean.

Here is an example SQL function to protect our ``article`` resource model:

.. code-block:: postgresql

    CREATE FUNCTION check_article_access(
            p_article_id integer,
            p_user_id integer) RETURNS boolean
        LANGUAGE plpgsql AS
    $$
    BEGIN

        -- always return true for superusers
        PERFORM * FROM users WHERE id = p_user_id AND is_superuser;
        IF FOUND THEN
            RETURN TRUE;
        END IF;

        -- return true if the user is the author of the article
        PERFORM *
        FROM articles
        WHERE id = p_article_id
          AND author_id = p_user_id;
        IF found THEN
            RETURN TRUE;
        END IF;

        -- check if the user has read access
        PERFORM *
        FROM article_read_access
        WHERE article_id = p_article_id
          AND user_id = p_user_id;
        RETURN found;
    END;
    $$;

In addition, the :attr:`user <Model.user>` attribute of the model must evaluate to an object representing the
user in whose behalf the request is made, i.e. the current (logged-in) user::

    class User:

        def __init__(user_id, ...):
            self.id = user_id
            ...

In a WSGI application, the variable holding this object must be thread-safe.
For this purpose you may want to use ``LocalProxy`` from the ``werkzeug`` library::

    from werkzeug.local import LocalProxy
    from quart import g

    current_user = LocalProxy(lambda: g.get('user'))

.. note::
    The authentication layer should be responsible for ensuring the value of this variable is set correctly
    (this is outside the scope of this article).

As an example, to protect the ``article`` resource model, we redefine it as follows:

.. code-block:: python
    :emphasize-lines: 4,5

    import sqlalchemy as sa
    from auth import current_user

    class ArticleModel(Model):
        from_ = articles_t
        fields = ('title', 'body', 'created_on', ...)
        access = sa.func.check_article_access
        user = current_user

If the current_user variable evaluates to ``None``, access is not granted for all objects of this type, otherwise
access is granted if the supplied function returns ``TRUE``.

When fetching a single object, or a related object in a to-one relationship a :exc:`Forbidden <jsonapi.exc.Forbidden>`
exception is raised if no user is logged in or the current user does not have access to the object in question::

    >>> await ArticleModel().get_object({}, 1)
    Traceback (most recent call last):
      ...
    jsonapi.exc.Forbidden: [ArticleModel] access denied for: article(1)
    >>> await ArticleModel().get_related({}, 1, 'author')
    Traceback (most recent call last):
      ...
    jsonapi.exc.Forbidden: [ArticleModel] access denied for: article(1)

When fetching a collection or related objects in a to-many relationship, objects to which access is not granted are
silently excluded from the response.
