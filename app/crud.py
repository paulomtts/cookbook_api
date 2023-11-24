from app.models import Categories, Units, Recipes, Ingredients, RecipeIngredients
from app.queries import CATEGORY_QUERY, UNIT_QUERY, RECIPE_QUERY, INGREDIENT_QUERY, RECIPE_INGREDIENT\
                        , RECIPE_COMPOSITION_EMPTY_QUERY, RECIPE_COMPOSITION_LOADED_QUERY\
                        , RECIPE_COMPOSITION_SNAPSHOT_QUERY
from setup import db


from fastapi import APIRouter, Response, status, Body
from fastapi.responses import JSONResponse, Response
from sqlalchemy import or_, and_
from sqlmodel import text

import pandas as pd
import json


crud_router = APIRouter()


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

table_switch = {
    'categories': Categories
    , 'units': Units
    , 'recipes': Recipes
    , 'ingredients': Ingredients
    , 'recipe_ingredients': RecipeIngredients
}


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


# @crud_router.post("/crud/insert", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
@crud_router.post("/crud/insert")
async def crud__insert(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:

    """
    Insert a new row into a table. Data example:
    >>> {
    >>>    "name": "Some name"
    >>> }
    """

    table_cls = table_switch[table_name]
    table_object = table_cls(**data)

    messages = {
        'client': f"Inserted data in {table_name.capitalize()}s."
        , 'logger': f"Insert in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    }
    _, status_code, message = db.insert(table_object, messages)
   
    return JSONResponse(status_code=status_code, content={'message': message}, headers=response.headers)


@crud_router.post("/crud/select")
async def crud__select(response: Response, table_name: str = None, structured: bool = False, data: dict = Body(...)) -> JSONResponse:
    """
    Query the database for a table. The statements used here are meant to make
    tables readable, often joining with other tables so as to provide more than
    foreign id's on a given column.
    
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

    * In case of no filters, simply omit the "filters" key.
    """
    df: pd.DataFrame
    

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


    read_data = lambda: pd.read_sql(statement, db.engine)
    messages = {
        'client': f"{table_name.replace('_', ' ').capitalize()}s retrieved."
        , 'logger': f"Querying <{table_name}> was succesful! Filters: {filters}"
    }

    df, status_code, message = db.touch(read_data, messages=messages, is_select=True)


    if status_code != 200:
        return JSONResponse(status_code=status_code, content={'message': message}, headers=response.headers)

    if status_code == 204:
        return Response(status_code=status_code, headers=response.headers)
    

    if 'created_at' in df.columns: df['created_at'] = df['created_at'].astype(str)
    if 'updated_at' in df.columns: df['updated_at'] = df['updated_at'].astype(str)
        
    json_data = df.to_json(orient='records')

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@crud_router.post("/crud/update")
async def crud__update(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Insert a new row into a table.
    """

    table_cls = table_switch[table_name]
    row_id = data.pop('id')

    messages = {
        'client': f"{table_name.capitalize()} updated."
        , 'logger': f"Update in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    }
    _, status_code, message = db.update_bulk(table_cls, [table_cls.id == row_id], data, messages)

    return JSONResponse(status_code=status_code, content={"message": message}, headers=response.headers)


@crud_router.post("/crud/update_bulk")
async def crud__update_build(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Insert a new row into a table.
    """

    table_cls = table_switch[table_name]
    pairings = [(table_cls.id == row.pop('id'), row) for row in data.values()]

    messages = {
        'client': f"{table_name.capitalize()} updated."
        , 'logger': f"Update in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    }
    _, status_code, message = db.update_bulk(table_cls, pairings, messages)

    return JSONResponse(status_code=status_code, content={"message": message}, headers=response.headers)


@crud_router.post("/crud/delete")
async def crud__delete(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Delete a row from a table. Filters example:
    >>> {
    >>>    'id': [1, 2, 3]
    >>> }
    """

    filters = data.pop('filters')
    if not filters:
        db.logger.warning(f"Client did not provide any filters.")
        return JSONResponse(status_code=400, content={"message": "No filters were received by the server."}, headers=response.headers)

    table_cls = table_switch[table_name]

    messages = {
        'client': f"{table_name.capitalize()} deleted."
        , 'logger': f"Delete in {table_name.capitalize()} was successful. \n\nFilters: {filters}\n"
    }
    _, status_code, message = db.delete(table_cls, filters, messages)
    
    return JSONResponse(status_code=status_code, content={"message": message}, headers=response.headers)


@crud_router.post("/crud/insert_bulk")
async def crud__insert_bulk(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Insert multiple rows into a table. Data example:
    >>> [
    >>>    {
    >>>        "name": "Some name"
    >>>    },
    >>>    {
    >>>        "name": "Some other name"
    >>>    }
    >>> ]
    """

    table_cls = table_switch[table_name]
    data_list = [row for _, row in data.items()]

    messages = {
        'client': f"Succesfully inserted data in {table_name.capitalize()}."
        , 'logger': f"Insert in {table_name.capitalize()} was successful. \n\nData: {data_list}\n"
    }
    _, status_code, message = db.bulk_insert(table_cls, data_list, messages)

    return JSONResponse(status_code=status_code, content={'message': message}, headers=response.headers)