from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm.exc import StaleDataError

from app.core.methods import api_output
from app.core.orm import UnchangedStateError
from app.core.models import  Recipes, RecipeIngredients
from app.core.queries import RECIPE_COMPOSITION_LOADED_QUERY as LOADED_QUERY\
                            , RECIPE_COMPOSITION_EMPTY_QUERY as EMPTY_QUERY
from app.core.schemas import APIOutput, DBOutput, DeleteFilters, SuccessMessages, QueryFilters
from app.custom.schemas import CSTSubmitRecipeInput, CSTDeleteRecipeInput
from setup import db

import pandas as pd


customRoutes_router = APIRouter()


@customRoutes_router.get("/custom/maps")
async def maps(response: Response) -> JSONResponse:
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
async def submit_recipe(input: CSTSubmitRecipeInput) -> APIOutput:
    form_data = input.form_data

    reference = input.reference
    filters = QueryFilters(and_={'id_recipe': [form_data.get('id')]})

    keep_columns = [key for key in RecipeIngredients.__annotations__.keys()]

    new_state = pd.DataFrame(input.recipe_ingredients_rows)
    new_state = new_state.drop(['id'], axis=1)
    new_state = new_state.rename(columns={'id_recipe_ingredient': 'id'})
    new_state = new_state[keep_columns]


    @api_output
    @db.catching(messages=SuccessMessages('Recipe submitted successfully.'))
    def touch_database(form_data, reference: str, filters, new_state: pd.DataFrame) -> DBOutput:
        
        new_form_data = form_data.copy()
        db.upsert(Recipes, [new_form_data], single=True)

        old_state = db.query(RecipeIngredients, None, filters)
        is_greater = (old_state['updated_at'] > reference).any()
        
        if is_greater:
            raise StaleDataError('This recipe has been updated by another user. Please refresh the page and try again.')
        

        merged_df = old_state.merge(new_state, how='outer', indicator=True)
        merged_df['id'] = merged_df['id'].astype('Int64')
        
        if merged_df['_merge'].eq('both').all():
            raise UnchangedStateError('No changes were made to the recipe ingredients.')
        

        insert_df = merged_df.query('_merge == "right_only"')\
                             .drop(['id', 'created_at', 'updated_at', '_merge'], axis=1)
        update_df = merged_df.query('_merge == "both"')\
                             .drop(['updated_at', '_merge'], axis=1)
        delete_df = merged_df.query('_merge == "left_only"')\
                             .drop('_merge', axis=1)

        delete_filters = QueryFilters(and_={'id': delete_df['id'].tolist()})

        if not insert_df.empty: db.insert(RecipeIngredients, insert_df.to_dict('records'))
        if not update_df.empty: db.update(RecipeIngredients, update_df.to_dict('records'))
        if not delete_df.empty: db.delete(RecipeIngredients, delete_filters)

        db.session.commit()

        return {
            'form_data': form_data,
            'recipe_data': db.query(Recipes),
            'recipe_ingredient_loaded_data': db.query(None, LOADED_QUERY(form_data.get('id'))),
        }

    return touch_database(form_data, reference, filters, new_state)


@customRoutes_router.delete("/custom/delete_recipe")
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

    @api_output
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