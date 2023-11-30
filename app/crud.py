from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response

from app.queries import RECIPE_COMPOSITION_EMPTY_QUERY, RECIPE_COMPOSITION_LOADED_QUERY, RECIPE_COMPOSITION_SNAPSHOT_QUERY
from app.models import Categories, Units, Recipes, Ingredients, RecipeIngredients
from app.orm import SuccessMessages
from setup import db

from collections import namedtuple
import pandas as pd
import json


crud_router = APIRouter()


TABLE_MAP = {
    'categories': Categories
    , 'units': Units
    , 'recipes': Recipes
    , 'ingredients': Ingredients
    , 'recipe_ingredients': RecipeIngredients
}

ComplexQuery = namedtuple('ComplexQuery', ['statement', 'client_name'])
QUERY_MAP = {
    'recipe_composition_empty': ComplexQuery(RECIPE_COMPOSITION_EMPTY_QUERY, 'empty Recipe composition')
    , 'recipe_composition_loaded': ComplexQuery(RECIPE_COMPOSITION_LOADED_QUERY, 'loaded Recipe composition')
    , 'recipe_composition_snapshot': ComplexQuery(RECIPE_COMPOSITION_SNAPSHOT_QUERY, 'Recipe')
}


def to_json(content):
    if isinstance(content, pd.DataFrame):
        return content.to_json(orient='records')
    else:
        return json.dumps(content)


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

    table_cls = TABLE_MAP.get(table_name)
    if table_cls is None:
        db.logger.warning(f"Client provided invalid table name: {table_name}")
        return JSONResponse(status_code=400, content={"message": f"Invalid table name: {table_name}"}, headers=response.headers)
    
    messages = SuccessMessages(
        client=f"Successfuly submited to {table_name.capitalize()}."
        , logger=f"Insert in <{table_name.capitalize()}> was successful. Data: \n{data}\n"
    )

    @db.catching(messages=messages)
    def insert_data(table_cls, data):
        return db.insert(table_cls, [data])
    
    content, status_code, message = insert_data(table_cls, data)
    json_data = to_json(content)

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
  
    table_cls = TABLE_MAP.get(table_name)
    query = QUERY_MAP.get(table_name, ComplexQuery(None, None))

    
    statement = query.statement if not callable(query.statement)\
                                else query.statement(**data.get('lambda_args', {}))  
    
    if table_cls is None and statement is None:
        db.logger.warning(f"Incoming data did not pass validation.")
        return JSONResponse(status_code=400, content={"message": f"Client provided an invalid table name: <{table_name}>"}, headers=response.headers)

    filters: dict = data.get('filters', {})
    messages = SuccessMessages(
        client=f"{table_name.capitalize()[:-1]} retrieved." if table_cls else f"{query.client_name.capitalize()} retrieved."
        , logger=f"Querying <{table_name}> was succesful! Filters: {filters}"
    )

    @db.catching(messages=messages)
    def read_data(table_cls, statement, filters):
        return db.query(table_cls=table_cls, statement=statement, filters=filters) # uses either table_cls or statement

    content, status_code, message = read_data(table_cls, statement, filters)
    json_data = to_json(content)
    
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
    table_cls = TABLE_MAP.get(table_name)
    if table_cls is None:
        db.logger.warning(f"Client provided invalid table name: {table_name}")
        return JSONResponse(status_code=400, content={"message": f"Invalid table name: {table_name}"}, headers=response.headers)

    messages = SuccessMessages(
        client=f"{table_name.capitalize()} updated."
        , logger=f"Update in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    )

    @db.catching(messages=messages)
    def update_data(table_cls, data):
        return db.update(table_cls, [data])

    content, status_code, message = update_data(table_cls, data)
    json_data = to_json(content)

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
        db.logger.warning(f"Insufficient data provided by client.")
        return JSONResponse(status_code=400, content={"message": "No filters were received by the server."}, headers=response.headers)

    table_cls = TABLE_MAP.get(table_name)
    if table_cls is None:
        db.logger.warning(f"Client provided invalid table name: {table_name}")
        return JSONResponse(status_code=400, content={"message": f"Invalid table name: {table_name}"}, headers=response.headers)

    messages = SuccessMessages(
        client=f"{table_name.capitalize()} deleted."
        , logger=f"Delete in {table_name.capitalize()} was successful. \n\nFilters: {filters}\n"
    )

    @db.catching(messages=messages)
    def delete_data(table_cls, filters):
        return db.delete(table_cls, filters)
    
    content, status_code, message = delete_data(table_cls, filters)
    json_data = to_json(content)
    
    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)