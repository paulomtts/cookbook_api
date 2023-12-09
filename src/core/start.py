from core.orm import DBManager

import logging.config
import dotenv
import os

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG'
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG'
    }
})

logger = logging.getLogger('root')
logger.setLevel(logging.DEBUG)

# dotenv.load_dotenv()
db_type = os.getenv('DB_TYPE')
db_user = os.getenv('DB_USER')
db_database = os.getenv('DB_DATABASE')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')

db = DBManager(db_type, db_user, db_password, db_host, db_port, db_database, db_name, logger)