from fastapi.responses import JSONResponse
import uvicorn

from setup import app
from app.crud import crud_router
from app.routes import routes_router



app.include_router(crud_router)
app.include_router(routes_router)


@app.get('/health')
async def azuretest():
    from setup import db
    from app.models import Ingredients
    from collections import namedtuple
    import datetime

    Messages = namedtuple('Messages', ['client', 'logger'], defaults=['', ''])

    new_ingredient_1 = dict(id=2, name='Potatoes', description="Boil 'em, mash 'em, stick 'em in a stew!", type='Some Vegetable', updated_at=datetime.datetime.now())
    new_ingredient_2 = dict(id=99, name='Caesar Sauce', description="A delicious sauce! Wow!", type='Sauce', updated_at=datetime.datetime.now())
    new_ingredient_3 = dict(id=3, name='A test ingredient', description="This is a test ingredient", type='Test', updated_at=datetime.datetime.now())
    new_ingredient_4 = dict(name='Something else', description="This is a test ingredient", type='Test', updated_at=datetime.datetime.now())
    new_ingredient_5 = dict(name='Another test ingredient', description="This is a test ingredient", type='Test', updated_at=datetime.datetime.now())

    # results = db.insert(Ingredients, [new_ingredient_4, new_ingredient_5], Messages(client='Submission successful!', logger='Insert successful'), returning=False)
    # results = db.update(Ingredients, [new_ingredient_1, new_ingredient_2], Messages(client='Submission successful!', logger='Update successful'), returning=False)
    # results = db.upsert(Ingredients, [new_ingredient_1, new_ingredient_3], Messages(client='Submission successful!', logger='Upsert successful'), returning=False)
    results = db.delete(Ingredients, {'id': [3]}, Messages(client='Submission successful!', logger='Delete successful'), returning=False)

    print(results.content)
    
    return JSONResponse(status_code=200, content={"message": "healthy."})


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True, reload_dirs=[
        'app'
    ], port=8000)