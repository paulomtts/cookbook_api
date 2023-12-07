from fastapi import APIRouter, Depends

from app.core.queries import RECIPE_COMPOSITION_EMPTY_QUERY, RECIPE_COMPOSITION_LOADED_QUERY, RECIPE_COMPOSITION_SNAPSHOT_QUERY
from app.core.models import Categories, Units, Recipes, Ingredients, RecipeIngredients
from app.core.schemas import DBOutput, APIOutput, CRUDSelectInput, CRUDDeleteInput, CRUDInsertInput, CRUDUpdateInput
from app.core.schemas import SuccessMessages
from app.core.methods import api_output
from app.core.auth import validate_session
from setup import db

from collections import namedtuple


crud_router = APIRouter()


TABLE_MAP = {
    'categories': Categories
    , 'units': Units
    , 'recipes': Recipes
    , 'ingredients': Ingredients
    , 'recipe_ingredients': RecipeIngredients
}

ComplexQuery = namedtuple('ComplexQuery', ['statement', 'name'])
QUERY_MAP = {
    'recipe_composition_empty': ComplexQuery(RECIPE_COMPOSITION_EMPTY_QUERY, 'empty Recipe composition')
    , 'recipe_composition_loaded': ComplexQuery(RECIPE_COMPOSITION_LOADED_QUERY, 'loaded Recipe composition')
    , 'recipe_composition_snapshot': ComplexQuery(RECIPE_COMPOSITION_SNAPSHOT_QUERY, 'Recipe')
}


@crud_router.post("/crud/insert", dependencies=[Depends(validate_session)])
async def crud_insert(input: CRUDInsertInput) -> APIOutput:
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
    table_cls = TABLE_MAP.get(input.table_name)
    
    messages = SuccessMessages(
        client=f"Successfuly submited to {input.table_name.capitalize()}."
        , logger=f"Insert in <{input.table_name.capitalize()}> was successful. Data: {input.data}"
    )

    @api_output
    @db.catching(messages=messages)
    def touch_database(table_cls, data) -> DBOutput:
        return db.insert(table_cls, data)
    
    return touch_database(table_cls, input.data)


@crud_router.post("/crud/select", dependencies=[Depends(validate_session)])
async def crud_select(input: CRUDSelectInput) -> APIOutput:
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
    table_cls = TABLE_MAP.get(input.table_name)

    query = QUERY_MAP.get(input.table_name, ComplexQuery(None, None))
    statement = query.statement if not callable(query.statement)\
                                else query.statement(**input.lambda_kwargs if input.lambda_kwargs else {}) 
    messages = SuccessMessages(
        client=f"{input.table_name.capitalize()[:-1]} retrieved." if table_cls else f"{query.name.capitalize()} retrieved."
        , logger=f"Querying <{input.table_name}> was succesful! Filters: {input.filters}"
    )

    @api_output
    @db.catching(messages=messages)
    def touch_database(table_cls, statement, filters):
        return db.query(table_cls=table_cls, statement=statement, filters=filters)

    return touch_database(table_cls, statement, input.filters)


@crud_router.put("/crud/update", dependencies=[Depends(validate_session)])
async def crud_update(input: CRUDUpdateInput) -> APIOutput:
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
    table_cls = TABLE_MAP.get(input.table_name)

    messages = SuccessMessages(
        client=f"{input.table_name.capitalize()} updated."
        , logger=f"Update in {input.table_name.capitalize()} was successful. Data: {input.data}"
    )

    @api_output
    @db.catching(messages=messages)
    def touch_database(table_cls, data):
        return db.update(table_cls, [data])

    return touch_database(table_cls, input.data)


@crud_router.delete("/crud/delete", dependencies=[Depends(validate_session)])
async def crud_delete(input: CRUDDeleteInput) -> APIOutput:
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
    table_cls = TABLE_MAP.get(input.table_name)

    filters = {input.field: input.ids}
    messages = SuccessMessages(
        client=f"{input.table_name.capitalize()} deleted."
        , logger=f"Delete in {input.table_name.capitalize()} was successful. Filters: {filters}"
    )

    @api_output
    @db.catching(messages=messages)
    def touch_database(table_cls, filters):
        return db.delete(table_cls, filters)
    
    return touch_database(table_cls, filters)