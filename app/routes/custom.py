from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response

from app.core.models import  Recipes, RecipeIngredients
from app.core.orm import SuccessMessages
from app.core.queries import RECIPE_COMPOSITION_LOADED_QUERY as LOADED_QUERY, RECIPE_COMPOSITION_SNAPSHOT_QUERY as SNAPSHOT_QUERY
from setup import db


customRoutes_router = APIRouter()


@customRoutes_router.get("/custom/maps")
async def crud__maps(response: Response) -> JSONResponse:
    """
    Obtain the maps.json file.

    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The JSON response containing the json.</li>
        </ul>
    """

    try:
        status_code = 200
        with open('maps.json', 'r') as f:
            json_data = f.read()

        db.logger.info(f"Successfully loaded maps.json file.")
    except Exception as e:
        db.logger.error(f"Could not load maps.json file. Error: {e}")
        json_data = {}
        status_code = 400

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': 'Configs retrieved!'}, headers=response.headers)


@customRoutes_router.post("/custom/submit_recipe")
async def routes__submit_recipe(response: Response, data: dict = Body(...)) -> JSONResponse:
    """
    Submit a recipe to the database.

    <h3>Args:</h3>
        <ul>
        <li>data (dict): The request data containing the form data.</li>
        </ul>

    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The JSON response containing the submitted recipe data and a message.</li>
        </ul>
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

        form_object = db.upsert(Recipes, [form_data], single=True)
        print(form_object)
        
        db.upsert(RecipeIngredients, [{**row, 'id_recipe': form_object.id} for row in insert_rows])
        db.delete(RecipeIngredients, {'id': [row.get('id_recipe_ingredient') for row in delete_rows]})
        
        db.session.commit()

        recipes_df = db.query(Recipes)
        recipe_ingredients_loaded_df = db.query(None, LOADED_QUERY(form_object.id))
        recipe_ingredients_snapshot_df = db.query(None, SNAPSHOT_QUERY(form_object.id))

        json_data = {
            'form_data': form_object,
            'recipe_data': recipes_df.to_json(orient='records'),
            'recipe_ingredient_loaded_data': recipe_ingredients_loaded_df.to_json(orient='records'),
            'recipe_ingredient_snapshot_data': recipe_ingredients_snapshot_df.to_json(orient='records'),
        }

        return json_data
    
    json_data, status_code, message = upsert_recipe(form_data, insert_rows, delete_rows)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)