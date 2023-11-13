from app.orm import DBClient

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
import logging.config


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

db = DBClient('postgresql', 'postgres', 'postgres', 'localhost', '5432', 'postgres', 'cookbook', logger)
from app.models import Recipe
# db.insert_dummy_data(Recipe)
# db.insert_dummy_data(Recipe)
# db.insert_dummy_data(Recipe)
# db.insert_dummy_data(Recipe)
# db.insert_dummy_data(Recipe)
# db.insert_dummy_data(Recipe)