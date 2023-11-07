from app.models import Category, Unit, Recipe, Ingredient, RecipeIngredient
from app.queries import CATEGORY_QUERY, UNIT_QUERY, RECIPE_QUERY, INGREDIENT_QUERY, RECIPE_INGREDIENT_QUERY
from setup import db


from fastapi import APIRouter, Response, status, Body
from fastapi.responses import JSONResponse, Response
from sqlalchemy import or_, and_
from sqlmodel import text

import json


crud_router = APIRouter()


query_switch = {
    'category': CATEGORY_QUERY
    , 'unit': UNIT_QUERY
    , 'recipe': RECIPE_QUERY
    , 'ingredient': INGREDIENT_QUERY
    , 'recipe_ingredient': RECIPE_INGREDIENT_QUERY
}

table_switch = {
    'category': Category
    , 'unit': Unit
    , 'recipe': Recipe
    , 'ingredient': Ingredient
    , 'recipe_ingredient': RecipeIngredient
}


@crud_router.post("/crud/insert", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def crud_insert(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:

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
async def crud_select(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Query the database for a table. The statements used here are meant to make
    tables readable, often joining with other tables so as to provide more than
    foreign id's on a given column.
    
    The parameters should be formatted as follows:
    >>> {
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
    
    statement = query_switch[table_name]

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

    read_data = lambda statement: db.session.execute(statement).fetchall()
    messages = {
        'client': f"{table_name.capitalize()}s retrieved."
        , 'logger': f"Querying <{table_name}s> was succesful!"
    }
    results, status_code, message = db.touch(read_data, [statement], messages, True)

    results = [dict(row) for row in results]
    if results:
        json_data = json.dumps(results, default=str)
    else:
        json_data = json.dumps([{}], default=str)

    if status_code == 204:
        return Response(status_code=status_code, headers=response.headers)

    return JSONResponse(status_code=status_code, content={'data': json_data, 'message': message}, headers=response.headers)


@crud_router.post("/crud/update")
async def crud_update(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
    """
    Insert a new row into a table.
    """

    table_cls = table_switch[table_name]
    row_id = data.pop('id')

    messages = {
        'client': f"{table_name.capitalize()} updated."
        , 'logger': f"Update in {table_name.capitalize()} was successful. \n\nData: {data}\n"
    }
    _, status_code, message = db.update(table_cls, [table_cls.id == row_id], data, messages)

    return JSONResponse(status_code=status_code, content={"message": message}, headers=response.headers)


@crud_router.post("/crud/delete")
async def crud_delete(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
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


@crud_router.post("/crud/insert/bulk")
async def crud_insert_bulk(response: Response, table_name: str = None, data: dict = Body(...)) -> JSONResponse:
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
    data_list = data.get('json_data', [])
    print(data_list)

    messages = {
        'client': f"Succesfully inserted data in {table_name.capitalize()}."
        , 'logger': f"Insert in {table_name.capitalize()} was successful. \n\nData: {data_list}\n"
    }
    _, status_code, message = db.bulk_insert(table_cls, data_list, messages)

    return JSONResponse(status_code=status_code, content={'message': message}, headers=response.headers)