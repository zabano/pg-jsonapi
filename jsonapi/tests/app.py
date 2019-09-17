import logging
import os

from asyncpgsa import pg
from quart import Quart
from quart import jsonify
from quart import request

from jsonapi.db import Filter
from jsonapi.model import MIME_TYPE
from jsonapi.model import get_error_object
from jsonapi.tests.model import *

app = Quart('jsonapi-test')
app.config['JSONIFY_MIMETYPE'] = MIME_TYPE

if 'JSONAPI_DEBUG' in os.environ:
    logger = logging.getLogger('asyncpgsa.query')
    logger.addHandler(app.logger.handlers[0])
    logger.setLevel(logging.DEBUG)


@app.before_first_request
async def init():
    await pg.init(database='jsonapi', user='jsonapi', password='jsonapi', min_size=5, max_size=10)


@app.errorhandler(500)
def handle_api_error(e):
    return jsonify(get_error_object(e)), e.status if hasattr(e, 'status') else 500


@app.route('/users/')
async def users():
    return jsonify(await UserModel().get_collection(request.args))


@app.route('/users/<int:user_id>')
async def user(user_id):
    return jsonify(await UserModel().get_object(request.args, user_id))


@app.route('/users/<int:user_id>/articles/')
async def user_articles(user_id):
    return jsonify(await UserModel().get_related(request.args, user_id, 'articles'))


@app.route('/users/<int:user_id>/name')
async def user_name(user_id):
    return jsonify(await UserModel().get_related(request.args, user_id, 'name'))


@app.route('/articles/')
async def articles():
    filter_by = None
    if 'filter[is-published]' in request.args:
        filter_by = Filter(articles_t.c.is_published.is_(
            request.args['filter[is-published]'] == 't'))
    return jsonify(await ArticleModel().get_collection(request.args, filter_by=filter_by))


@app.route('/articles/<int:article_id>')
async def article(article_id):
    return jsonify(await ArticleModel().get_object(request.args, article_id))


@app.route('/articles/<int:article_id>/author')
async def article_author(article_id):
    return jsonify(await ArticleModel().get_related(request.args, article_id, 'author'))


@app.route('/articles/<int:article_id>/comments/')
async def article_comments(article_id):
    return jsonify(await ArticleModel().get_related(request.args, article_id, 'comments'))


@app.route('/articles/<int:article_id>/keywords/')
async def article_keywords(article_id):
    return jsonify(await ArticleModel().get_related(request.args, article_id, 'keywords'))


if __name__ == '__main__':
    app.run()
