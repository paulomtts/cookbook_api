from fastapi.responses import JSONResponse

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.start import app 
from src.core.crud import crud_router
from src.core.auth import auth_router
from src.custom.custom import customRoutes_router

import uvicorn


app.include_router(crud_router)
app.include_router(auth_router)
app.include_router(customRoutes_router)

@app.get('/health')
async def azuretest():
    return JSONResponse(status_code=200, content={"message": "healthy."})

# if __name__ == '__main__':
#     uvicorn.run('main:app', reload=False, reload_dirs=['app'], port=8001)