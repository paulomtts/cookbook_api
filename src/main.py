from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# from core.crud import crud_router
# from core.auth import auth_router
# from custom.custom import customRoutes_router
from core.orm import DBManager

import logging, logging.config
import uvicorn
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



app = FastAPI()
app.add_middleware( # necessary to allow requests from local services
    CORSMiddleware,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    allow_origins=['*'],
    allow_credentials=True,
)


dotenv.load_dotenv(f"{os.getcwd()}/../.env")
db_type = os.environ.get('DB_TYPE')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')
db_name = os.environ.get('DB_NAME')
db = DBManager(db_type, db_user, db_password, db_host, db_port, db_user, db_name, logger)


# app.include_router(crud_router)
# app.include_router(auth_router)
# app.include_router(customRoutes_router)

@app.get('/health')
async def azuretest():
    return JSONResponse(status_code=200, content={"message": "healthy."})

if __name__ == '__main__':
    uvicorn.run('main:app', reload=True, reload_dirs=['app'], port=8001)