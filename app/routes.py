from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response

from app.models import  Recipes, RecipeIngredients
from setup import db


routes_router = APIRouter()


@routes_router.post("/custom/submit_recipe")
async def routes__submit_recipe(response: Response, data: dict = Body(...)) -> JSONResponse:
    """
    Receives data from the Recipes form, as well as lists of rows to be inserted, updated, and deleted
    in RecipeIngredients. The data is then processed and inserted into the database.
    """
    form_data = data.get('form_data')
    insert_rows = data.get('insert_rows', [])
    update_rows = data.get('update_rows', [])
    delete_rows = data.get('delete_rows', [])

    if not form_data:
        db.logger.error(f"Could not find form data in request body.")
        message = "Could not find form data in request body."
        return JSONResponse(status_code=400, content={'message': message}, headers=response.headers)
    
    form_object = Recipes(**form_data)
    
    tasks = [
        lambda: db.insert(Recipes, [form_data], as_task_list=True)
        , lambda: db.session.flush()
        , *[lambda: db.session.add(RecipeIngredients(**{**row, 'id_recipe': form_object.id})) for row in insert_rows]
        , *[lambda: db.session.merge(RecipeIngredients(**row)) for row in update_rows]
        , *[lambda: db.session.delete(RecipeIngredients(**row)) for row in delete_rows]
    ]

    job_results = db.touch(tasks)

    if type(job_results) != list:
        status_code = job_results.status_code
        message = job_results.client_message
    else:
        status_code = 200
        message = "Successfully submitted recipe."

    return JSONResponse(status_code=status_code, content={'message': message}, headers=response.headers)