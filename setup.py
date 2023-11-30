from app.orm import DBManager

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
        'http://localhost:3000',
        'https://lmind-dashboard.azurewebsites.net',
        'http://localhost:8001',
        'https://lmindwsm.azurewebsites.net',
        'http://localhost:5173/',
        'http://localhost:5173',
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