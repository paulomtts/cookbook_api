from fastapi import APIRouter, Response, Body
from fastapi.responses import JSONResponse, Response

from app.core.queries import RECIPE_COMPOSITION_EMPTY_QUERY, RECIPE_COMPOSITION_LOADED_QUERY, RECIPE_COMPOSITION_SNAPSHOT_QUERY
from app.core.models import Categories, Units, Recipes, Ingredients, RecipeIngredients
from app.core.orm import SuccessMessages
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


@crud_router.post("/crud/insert")
async def crud__insert(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Inserts data into the specified table.

    <h3>Args:</h3>
        <ul>
        <li>table_name (str): The name of the table to insert data into.</li>
        <li>body (dict): Data in the form of a list of dictionaries.</li>
        </ul>

    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The JSON response containing the inserted data and a message.</li>
        </ul>
    """

    table_cls = TABLE_MAP.get(table_name)
    if table_cls is None:
        db.logger.warning(f"Client provided invalid table name: {table_name}")
        return JSONResponse(status_code=400, content={"message": f"Invalid table name: {table_name}"}, headers=response.headers)
    
    messages = SuccessMessages(
        client=f"Successfuly submited to {table_name.capitalize()}."
        , logger=f"Insert in <{table_name.capitalize()}> was successful. Data: {data}"
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
    <pre>
    <code>
    {
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
    </code>
    </pre>

    In case of no filters, simply omit the "filters" key.

    <h3>Args:</h3>
        <ul>
        <li>response (Response): The response object.</li>
        <li>table_name (str): The name of the table to select data from.</li>
        <li>data (dict): The request body containing the filters and other parameters.</li>
        </ul>
        
    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The response containing the selected data and a message.</li>
        </ul>
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


@crud_router.put("/crud/update")
async def crud__update(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Update a record in the specified table.

    <h3>Args:</h3>
        <ul>
        <li>table_name (str): The name of the table to update.</li>
        <li>data (dict): The data to update.</li>
        </ul>

    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The JSON response containing the updated data and message.</li>
        </ul>
    """
    table_cls = TABLE_MAP.get(table_name)
    if table_cls is None:
        db.logger.warning(f"Client provided invalid table name: {table_name}")
        return JSONResponse(status_code=400, content={"message": f"Invalid table name: {table_name}"}, headers=response.headers)

    messages = SuccessMessages(
        client=f"{table_name.capitalize()} updated."
        , logger=f"Update in {table_name.capitalize()} was successful. Data: {data}"
    )

    @db.catching(messages=messages)
    def update_data(table_cls, data):
        return db.update(table_cls, [data])

    content, status_code, message = update_data(table_cls, data)
    json_data = to_json(content)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@crud_router.delete("/crud/delete")
async def crud__delete(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Delete records from a specified table based on the provided filters. Filters example:
    <pre>
    <code>
    {
        'id': [1, 2, 3]
    }
    </code>
    </pre>

    <h3>Args:</h3>
        <ul>
        <li>table_name (str): The name of the table to delete records from.</li>
        <li>data (dict): The request body containing the filters.</li>
        </ul>

    <h3>Returns:</h3>
        <ul>
        <li>JSONResponse: The JSON response containing the deleted data and a message.</li>
        </ul>
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
        , logger=f"Delete in {table_name.capitalize()} was successful. Filters: {filters}"
    )

    @db.catching(messages=messages)
    def delete_data(table_cls, filters):
        return db.delete(table_cls, filters)
    
    content, status_code, message = delete_data(table_cls, filters)
    json_data = to_json(content)
    
    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)