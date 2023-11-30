from fastapi.responses import JSONResponse
import uvicorn

from setup import app
from app.crud import crud_router
from app.routes import routes_router


app.include_router(crud_router)
app.include_router(routes_router)


@app.get('/health')
async def azuretest():
    return JSONResponse(status_code=200, content={"message": "healthy."})

# if __name__ == '__main__':
#     uvicorn.run('main:app', reload=True, reload_dirs=[
#         'app'
#     ], port=8000)