from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.core.crud import crud_router
from core.auth import auth_router
from custom.custom import customRoutes_router

import uvicorn

app = FastAPI()
app.add_middleware( # necessary to allow requests from local services
    CORSMiddleware,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    allow_origins=['*'],
    allow_credentials=True,
)

app.include_router(crud_router)
app.include_router(auth_router)
app.include_router(customRoutes_router)


@app.get('/health')
async def azuretest():
    return JSONResponse(status_code=200, content={"message": "healthy."})

# if __name__ == '__main__':
#     uvicorn.run('main:app', reload=True, reload_dirs=['app'], port=8001)