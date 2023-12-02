from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response

from app.core.models import  Recipes, RecipeIngredients
from app.core.orm import SuccessMessages
from app.core.queries import RECIPE_COMPOSITION_LOADED_QUERY as LOADED_QUERY\
                            , RECIPE_COMPOSITION_SNAPSHOT_QUERY as SNAPSHOT_QUERY\
                            , RECIPE_COMPOSITION_EMPTY_QUERY as EMPTY_QUERY
from app.core.schemas import DefaultOutput, DeleteData
from app.custom.schemas import RecipeDeleteInput, RecipeDeleteOutput
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
async def submit_recipe(response: Response, data: dict = Body(...)) -> JSONResponse:
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
    def touch__submit_recipe(form_data, insert_rows, delete_rows):

        form_object = db.upsert(Recipes, [form_data], single=True)  
        db.upsert(RecipeIngredients, [{**row, 'id_recipe': form_object.id, 'updated_at': None} for row in insert_rows])
        db.delete(RecipeIngredients, {'id': [row.get('id_recipe_ingredient') for row in delete_rows]})
        
        db.session.commit()

        recipes_df = db.query(Recipes)
        recipe_ingredients_loaded_df = db.query(None, LOADED_QUERY(form_object.id))
        recipe_ingredients_snapshot_df = db.query(None, SNAPSHOT_QUERY(form_object.id))

        json_data = {
            'form_data': form_object.as_json,
            'recipe_data': recipes_df.to_json(orient='records'),
            'recipe_ingredient_loaded_data': recipe_ingredients_loaded_df.to_json(orient='records'),
            'recipe_ingredient_snapshot_data': recipe_ingredients_snapshot_df.to_json(orient='records'),
        }

        return json_data
    
    json_data, status_code, message = touch__submit_recipe(form_data, insert_rows, delete_rows)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@customRoutes_router.delete("/custom/delete_recipe")
# async def delete_recipe(response: Response, data: RecipeDeleteInput) -> DefaultOutput:
async def delete_recipe(response: Response, data: RecipeDeleteInput) -> RecipeDeleteOutput:
    """
    Delete a recipe from the database. The body should be as follows:
    <pre>
    <code>
    {
        "id": [1]
    }
    </code>
    </pre>

    <h3>Args:</h3>
        <ul>
        <li>data (dict): The request data containing the id of the form to be deleted.</li>
        </ul>

    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The JSON response containing the updated recipes and recipe ingredients table, and a message.</li>
        </ul>
    """

    @db.catching(messages=SuccessMessages('Recipe deleted successfully.'))
    def touch(recipe: DeleteData, composition: DeleteData):
        
        db.delete(RecipeIngredients, {composition.field: composition.ids})
        db.delete(Recipes, {recipe.field: recipe.ids})
        db.session.commit()

        recipes_df = db.query(Recipes)
        recipe_ingredients_empty_df = db.query(None, EMPTY_QUERY)

        json_data = {
            'recipe_data': recipes_df.to_json(orient='records'),
            'recipe_ingredient_empty_data': recipe_ingredients_empty_df.to_json(orient='records'),
        }

        return json_data
    
    json_data, status_code, message = touch(data.recipe, data.composition)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)
    # @db.catching(messages=SuccessMessages('Recipe deleted successfully.'))
    # def touch__delete_recipe(recipe: DeleteData, composition: DeleteData):
        
    #     db.delete(RecipeIngredients, {composition.field: composition.ids})
    #     db.delete(Recipes, {recipe.field: recipe.ids})
    #     db.session.commit()

    #     recipes = db.query(Recipes).to_json(orient='records')
    #     recipe_ingredients = db.query(None, EMPTY_QUERY).to_json(orient='records')
    #     # recipe_ingredients = db.query(Recipes, EMPTY_QUERY).to_json(orient='records')

    #     content = RecipeDeleteOutput(
    #         recipes = recipes
    #         , recipe_ingredients = recipe_ingredients
    #     )

    #     return DefaultOutput(
    #         data = content
    #         , status = 200
    #         , message = 'Recipe deleted successfully.'
    #     )

    #     # json_data = {
    #     #     'recipe_data': recipes.to_json(orient='records'),
    #     #     'recipe_ingredient_empty_data': recipe_ingredients.to_json(orient='records'),
    #     # }

    #     # return json_data
    
    # # json_data, status_code, message = touch__delete_recipe(data.recipe, data.composition)
    # result = touch__delete_recipe(data.recipe, data.composition)

    # # return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)
    # # return json_data
    # return result