import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from core import orm
import logging.config
import dotenv

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

from boto.s3.connection import S3Connection
db_type = S3Connection(os.environ['DB_TYPE'], os.environ['DB_TYPE'])
db_user = S3Connection(os.environ['DB_USER'], os.environ['DB_USER'])
db_password = S3Connection(os.environ['DB_PASSWORD'], os.environ['DB_PASSWORD'])
db_host = S3Connection(os.environ['DB_HOST'], os.environ['DB_HOST'])
db_port = S3Connection(os.environ['DB_PORT'], os.environ['DB_PORT'])
db_name = S3Connection(os.environ['DB_NAME'], os.environ['DB_NAME'])

# dotenv.load_dotenv()
# db_type = os.environ.get('DB_TYPE')
# db_user = os.environ.get('DB_USER')
# db_password = os.environ.get('DB_PASSWORD')
# db_host = os.environ.get('DB_HOST')
# db_port = os.environ.get('DB_PORT')
# db_name = os.environ.get('DB_NAME')

# db = orm.DBManager(db_type, db_user, db_password, db_host, db_port, db_user, db_name, logger)