from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse, Response

from app.core.methods import api_output
from app.core.models import  Recipes, RecipeIngredients
from app.core.queries import RECIPE_COMPOSITION_LOADED_QUERY as LOADED_QUERY\
                            , RECIPE_COMPOSITION_SNAPSHOT_QUERY as SNAPSHOT_QUERY\
                            , RECIPE_COMPOSITION_EMPTY_QUERY as EMPTY_QUERY
from app.core.schemas import APIOutput, DBOutput, DeleteFilters, SuccessMessages
from app.custom.schemas import CSTSubmitRecipeInput, CSTDeleteRecipeInput
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
@api_output
async def submit_recipe(input: CSTSubmitRecipeInput) -> APIOutput:
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

    form_data = input.form_data
    upsert_rows = input.insert_rows + input.update_rows
    delete_rows = input.delete_rows

    form_data.pop('id', None)

    @db.catching(messages=SuccessMessages('Recipe submitted successfully.'))
    def touch_database(form_data, insert_rows, delete_rows) -> DBOutput:

        form_object = db.upsert(Recipes, [form_data], single=True)  
        db.upsert(RecipeIngredients, [{**row, 'id_recipe': form_object.id, 'updated_at': None} for row in insert_rows])
        db.delete(RecipeIngredients, {'id': [row.get('id_recipe_ingredient') for row in delete_rows]})
        
        db.session.commit()

        recipes_df = db.query(Recipes)
        recipe_ingredients_loaded_df = db.query(None, LOADED_QUERY(form_object.id))
        recipe_ingredients_snapshot_df = db.query(None, SNAPSHOT_QUERY(form_object.id))

        return {
            'form_data': form_object,
            'recipe_data': recipes_df,
            'recipe_ingredient_loaded_data': recipe_ingredients_loaded_df,
            'recipe_ingredient_snapshot_data': recipe_ingredients_snapshot_df,
        }
    
    return touch_database(form_data, upsert_rows, delete_rows)


@customRoutes_router.delete("/custom/delete_recipe")
@api_output
async def delete_recipe(input: CSTDeleteRecipeInput) -> APIOutput:
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
    def touch_database(recipe: DeleteFilters, composition: DeleteFilters) -> DBOutput:
        
        db.delete(RecipeIngredients, {composition.field: composition.values})
        db.delete(Recipes, {recipe.field: recipe.values})
        db.session.commit()

        recipes = db.query(Recipes)
        recipe_ingredients = db.query(None, EMPTY_QUERY)

        return {
            'recipes': recipes,
            'recipe_ingredients': recipe_ingredients
        }

    return touch_database(input.recipe, input.composition)