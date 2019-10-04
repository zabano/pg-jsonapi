import logging
import os

from quart import Quart, jsonify, request

from jsonapi.model import MIME_TYPE, get_error_object
from jsonapi.tests.auth import login, logout
from jsonapi.tests.model import *

app = Quart('jsonapi-test')
app.config['JSONIFY_MIMETYPE'] = MIME_TYPE

logging.getLogger('quart.app').setLevel(logging.CRITICAL)

if 'JSONAPI_DEBUG' in os.environ:
    logger = logging.getLogger('asyncpgsa.query')
    logger.addHandler(app.logger.handlers[0])
    logger.setLevel(logging.DEBUG)


@app.before_first_request
async def init():
    await init_db()


@app.before_request
async def login_user():
    if 'JSONAPI_LOGIN' in os.environ:
        user_id = os.environ['JSONAPI_LOGIN']
        login(user_id)
    else:
        logout()


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
    return jsonify(await ArticleModel().get_collection(request.args))


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


@app.route('/articles/<term>')
async def search_articles(term):
    return jsonify(await ArticleModel().get_collection(request.args, search=term))


@app.route('/search/<term>')
async def search(term):
    return jsonify(await SearchModel().search(request.args, term))


if __name__ == '__main__':
    app.run()
