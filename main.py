from fastapi.responses import JSONResponse
import uvicorn

from setup import app
from app.core.crud import crud_router
from app.core.auth import auth_router
from app.custom.custom import customRoutes_router



app.include_router(crud_router)
app.include_router(auth_router)
app.include_router(customRoutes_router)

@app.get('/health')
async def azuretest():
    return JSONResponse(status_code=200, content={"message": "healthy."})

if __name__ == '__main__':
    uvicorn.run('main:app', reload=False, reload_dirs=['app'], port=8000)