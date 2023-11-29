from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text, or_, and_

from app.models import Categories, Units, Recipes, Ingredients, RecipeIngredients
from app.queries import CATEGORY_QUERY, UNIT_QUERY, RECIPE_QUERY, INGREDIENT_QUERY, RECIPE_INGREDIENT\
                        , RECIPE_COMPOSITION_EMPTY_QUERY, RECIPE_COMPOSITION_LOADED_QUERY\
                        , RECIPE_COMPOSITION_SNAPSHOT_QUERY
from app.orm import SuccessMessages
from setup import db

import pandas as pd
import json


crud_router = APIRouter()


table_switch = {
    'categories': Categories
    , 'units': Units
    , 'recipes': Recipes
    , 'ingredients': Ingredients
    , 'recipe_ingredients': RecipeIngredients
}

query_switch = {
    'categories': CATEGORY_QUERY
    , 'units': UNIT_QUERY
    , 'recipes': RECIPE_QUERY
    , 'ingredients': INGREDIENT_QUERY
    , 'recipe_ingredients': RECIPE_INGREDIENT
    , 'recipe_composition_empty': RECIPE_COMPOSITION_EMPTY_QUERY
    , 'recipe_composition_loaded': RECIPE_COMPOSITION_LOADED_QUERY
    , 'recipe_composition_snapshot': RECIPE_COMPOSITION_SNAPSHOT_QUERY
}

callable_queries = [RECIPE_COMPOSITION_LOADED_QUERY, RECIPE_COMPOSITION_SNAPSHOT_QUERY]


@crud_router.get("/crud/maps")
async def crud__maps(response: Response) -> JSONResponse:
    """
    Returns the local maps.json file.
    """

    try:
        status_code = 200
        with open('app/maps.json', 'r') as f:
            json_data = json.load(f)

        db.logger.info(f"Successfully loaded maps.json file.")
    except Exception as e:
        db.logger.error(f"Could not load maps.json file. Error: {e}")
        json_data = {}
        status_code = 400

    return JSONResponse(status_code=status_code, content=json_data, headers=response.headers)


@crud_router.post("/crud/insert")
async def crud__insert(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Inserts data into the specified table.

    Args:
        - response (Response): The response object.
        - table_name (str): The name of the table to insert data into.
        - data (dict): The data to be inserted.

    Returns:
        - JSONResponse: The JSON response containing the inserted data and a message.
    """
    table_cls = table_switch[table_name]

    messages = SuccessMessages(
        f"Inserted data in {table_name.capitalize()}s."
        , f"Insert in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    )
    content, status_code, message = db.insert(table_cls, [data], messages, returning=True, as_task=False)
    json_data = content.to_json(orient='records')

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@crud_router.post("/crud/select")
async def crud__select(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Selects data from a specified table in the database based on the provided filters.

    The parameters should be formatted as follows:
    >>> {
            "lambda_args": {
                "arg1": "value1",
                "arg2": "value2",
            }
            "filters": {
                "or": {
                    "name": ["value1", "value2"],
                },
                "and": {
                    "id": [1]
                },
                "like": {
                    "name": ["aaa", "bbb"],
                },
                "not_like": {
                    "name": ["ccc"],
                },      
            }
        }

    *In case of no filters, simply omit the "filters" key.

    Args:
        - response (Response): The response object.
        - table_name (str): The name of the table to select data from.
        - data (dict): The request body containing the filters and other parameters.

    Returns:
        - JSONResponse: The response containing the selected data and a message.
    """
    content: pd.DataFrame
    

    statement = query_switch[table_name]

    if statement in callable_queries:
        callable_args = data.get('lambda_args', {})
        statement = statement(**callable_args)


    filters: dict = data.get('filters', {})
    conditions: list = []

    if 'or' in filters:
        or_conditions = [text(f"{attr} = {val}") for attr, values in filters['or'].items() for val in values]
        conditions.append(or_(*or_conditions))

    if 'and' in filters:
        and_conditions = [text(f"{attr} = {val}") for attr, values in filters['and'].items() for val in values]
        conditions.append(and_(*and_conditions))

    if 'like' in filters:
        like_conditions = [text(f"{attr} LIKE {val}") for attr, values in filters['like'].items() for val in values]
        conditions.append(or_(*like_conditions))

    if 'not_like' in filters:
        not_like_conditions = [text(f"{attr} NOT LIKE {val}") for attr, values in filters['like'].items() for val in values]
        conditions.append(and_(*not_like_conditions))

    if conditions:
        statement = statement.where(and_(*conditions))

    messages = SuccessMessages(
        f"{table_name.replace('_', ' ').capitalize()}s retrieved."
        , f"Querying <{table_name}> was succesful! Filters: {filters}"
    )

    @db.catching(messages=messages)
    def read_data(statement):
        return pd.read_sql(statement, db.engine)

    content, status_code, message = read_data(statement)

    if isinstance(content, pd.DataFrame):
        json_data = content.to_json(orient='records')
    
    if status_code == 204:
        return Response(status_code=status_code, headers=response.headers)

    if status_code != 200:
        return JSONResponse(status_code=status_code, content={'message': message}, headers=response.headers)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@crud_router.post("/crud/update")
async def crud__update(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Update a record in the specified table.

    Args:
        - response (Response): The response object.
        - table_name (str): The name of the table to update.
        - data (dict): The data to update.

    Returns:
        - JSONResponse: The JSON response containing the updated data and message.
    """
    table_cls = table_switch[table_name]

    messages = SuccessMessages(
        client=f"{table_name.capitalize()} updated."
        , logger=f"Update in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    )
    content, status_code, message = db.update(table_cls, [data], messages, returning=True, as_task=False)
    json_data = content.to_json(orient='records')

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@crud_router.post("/crud/delete")
async def crud__delete(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Delete records from a specified table based on the provided filters. Filters example:
    >>> {'id': [1, 2, 3]}

    Args:
        - response (Response): The response object.
        - table_name (str): The name of the table to delete records from.
        - data (dict): The request body containing the filters.

    Returns:
        - JSONResponse: The JSON response containing the deleted data and a message.
    """
    filters = data.pop('filters')

    if not filters:
        db.logger.warning(f"Client did not provide any filters.")
        return JSONResponse(status_code=400, content={"message": "No filters were received by the server."}, headers=response.headers)

    table_cls = table_switch[table_name]

    messages = SuccessMessages(
        client=f"{table_name.capitalize()} deleted."
        , logger=f"Delete in {table_name.capitalize()} was successful. \n\nFilters: {filters}\n"
    )
    content, status_code, message = db.delete(table_cls, filters, messages, returning=True, as_task=False)
    json_data = content.to_json(orient='records')
    
    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)