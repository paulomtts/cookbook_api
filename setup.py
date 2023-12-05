from app.core.orm import DBManager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging, logging.config
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


app = FastAPI()
app.add_middleware( # necessary to allow requests from local services
    CORSMiddleware,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    allow_origins=[
        "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=546852036472-m2b8gvcuqngij6lneigefiuhsqgr08pd.apps.googleusercontent.com&redirect_uri=http://localhost/callback&scope=openid%20profile%20email&access_type=offline"
        # 'http://localhost:5173/',
        'http://localhost:8000/',
    ],
    allow_credentials=True,
)


dotenv.load_dotenv()
db_type = os.environ.get('DB_TYPE')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')

try:
    if all([db_type, db_user, db_password, db_host, db_port, db_name]):
        db = DBManager(db_type, db_user, db_password, db_host, db_port, db_user, db_name, logger)
    else:
        raise Exception('Could not find all environment variables for database connection.')
except Exception as e:
    logger.error(e)