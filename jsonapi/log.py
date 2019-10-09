import os
import logging
import sqlparse

log_format = '[jsonapi] %(message)s'

logging.basicConfig(format=log_format)

logger = logging.getLogger('jsonapi')

if 'JSONAPI_DEBUG' in os.environ:
    logger.setLevel(logging.INFO)


def log_query(query):
    logger.info(sqlparse.format(str(query), reindent=True, keyword_case='upper'))
