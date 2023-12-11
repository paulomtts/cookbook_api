from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.core.crud import crud_router
from src.core.auth import auth_router
from src.custom.custom import customRoutes_router

app = FastAPI()
app.add_middleware( # necessary to allow requests from local services
    CORSMiddleware,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    # allow_origins=['*'],
    # allow_origins=['https://cbk-frt-a0-0-4-d329a0a2f76c.herokuapp.com', 'https://cbk-frt.azurewebsites.net', 'http://localhost:5173'],
    allow_origins=['https://cbk-frt-a0-0-4-d329a0a2f76c.herokuapp.com', 'https://cbk-frt.azurewebsites.net'],
    allow_credentials=True,
)

app.include_router(crud_router)
app.include_router(auth_router)
app.include_router(customRoutes_router)


@app.get('/health')
async def azuretest():
    return JSONResponse(status_code=200, content={"message": "healthy."})

# if __name__ == '__main__':
#     uvicorn.run('main:app', reload=True, reload_dirs=['app'], port=8000)
