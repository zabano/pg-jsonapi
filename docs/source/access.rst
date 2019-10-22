#################
Protecting Models
#################

.. include:: warning.rst

.. currentmodule:: jsonapi.model

A model can be protected by setting the :attr:`access <Model.access>` attribute of the model to an SQL function that
accepts two arguments: the ``id`` of the resource object and the current (logged-in) user id, and return a boolean.

Returning a ``TRUE`` value grants user access the resource object, otherwise access is not granted.

Here is an example SQL function to protect our ``article`` resource model:

.. code-block:: postgresql

    CREATE FUNCTION check_article_access(
            p_article_id integer,
            p_user_id integer) RETURNS boolean
        LANGUAGE plpgsql AS
    $$
    BEGIN

        -- return true if the user is a global admin
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

        -- if the user is not granted read access, raise an exception
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
    The authentication layer should be responsible for ensuring the value of this variable is set correctly (this is
    outside the scope of this article). If the value of this

As an example, to protect the ``article`` resource model, we redefine it as follows::

    class ArticleModel(Model):
        from_ = articles_t
        fields = (...)
        access = func.check_article_access
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
simply not included in the response and no error is raised.

