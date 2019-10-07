import os
import logging

log_format = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'

logging.basicConfig(format=log_format)

logger = logging.getLogger('jsonapi')

if 'JSONAPI_DEBUG' in os.environ:
    logger.setLevel(logging.INFO)
    for mode in set(os.environ['JSONAPI_DEBUG'].split(',')):
        if mode == 'sql':
            logging.getLogger('asyncpgsa.query').setLevel(logging.DEBUG)
        elif mode == 'on':
            logger.setLevel(logging.DEBUG)
        elif mode == 'off':
            logger.setLevel(logging.WARN)
