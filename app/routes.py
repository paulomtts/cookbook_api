from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response

from app.models import  Recipes, RecipeIngredients
from app.orm import SuccessMessages
from app.queries import RECIPE_COMPOSITION_LOADED_QUERY as LOADED_QUERY, RECIPE_COMPOSITION_SNAPSHOT_QUERY as SNAPSHOT_QUERY
from setup import db

import pandas as pd
import datetime

routes_router = APIRouter()


@routes_router.post("/custom/submit_recipe")
async def routes__submit_recipe(response: Response, data: dict = Body(...)) -> JSONResponse:
    """
    Submit a recipe to the database.

    Args:
        - response (Response): The response object.
        - data (dict): The request data containing the form data.

    Returns:
        - JSONResponse: The JSON response containing the submitted recipe data and a message.
    """

    form_data: dict = data.get('form_data')


    if not form_data:
        db.logger.error(f"Could not find form data in request body.")
        message = "Could not find form data in request body."
        return JSONResponse(status_code=400, content={'message': message}, headers=response.headers)

    if form_data.get('id', '') == '': # reason: if not found or empty
        form_data.pop('id')

    insert_rows = data.get('insert_rows', []) + data.get('update_rows', [])
    delete_rows = data.get('delete_rows', [])


    @db.catching(messages=SuccessMessages('Recipe submitted successfully.'))
    def upsert_recipe(form_data, insert_rows, delete_rows):

        form_object: Recipes = db.upsert(Recipes, [form_data], single=True)
        
        db.upsert(RecipeIngredients, [{**row, 'id_recipe': form_object.id} for row in insert_rows])
        db.delete(RecipeIngredients, {'id': [row.get('id_recipe_ingredient') for row in delete_rows]})
        
        db.session.commit()

        new_form_data = form_object.json()
        recipes_df = db.query(Recipes)
        recipe_ingredients_loaded_df = pd.DataFrame(db.session.execute(LOADED_QUERY(form_object.id)))
        recipe_ingredients_snapshot_df = pd.DataFrame(db.session.execute(SNAPSHOT_QUERY(form_object.id)))

        json_data = {
            'form_data': new_form_data,
            'recipe_data': recipes_df.to_json(orient='records'),
            'recipe_ingredient_loaded_data': recipe_ingredients_loaded_df.to_json(orient='records'),
            'recipe_ingredient_snapshot_data': recipe_ingredients_snapshot_df.to_json(orient='records'),
        }

        return json_data
    
    json_data, status_code, message = upsert_recipe(form_data, insert_rows, delete_rows)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)