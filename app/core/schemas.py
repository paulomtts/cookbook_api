from pydantic import BaseModel, validator
from typing import List, Any, Optional, Literal


import pandas as pd
import json

class TableNames(BaseModel):
    table_name: Literal['units'] | Literal['categories'] | Literal['ingredients'] | Literal['recipes'] | Literal['recipe_ingredients'] | Literal['recipe_composition_empty'] | Literal['recipe_composition_loaded'] | Literal['recipe_composition_snapshot']

    @validator('table_name')
    def validate_table_name(cls, value):
        if value not in ['units', 'categories', 'ingredients', 'recipes', 'recipe_ingredients', 'recipe_composition_empty', 'recipe_composition_loaded', 'recipe_composition_snapshot']:
            raise ValueError(f"Invalid table name.")
        return value
    
class QueryFilters(BaseModel):
    or_: Optional[dict[str, List[str | int]]]
    and_: Optional[dict[str, List[str | int]]]
    like_: Optional[dict[str, List[str | int]]]
    not_like_: Optional[dict[str, List[str | int]]]

class QueryArgs(BaseModel):
    kwargs: Optional[dict[str, Any]]


class DBOutput(BaseModel):
    """
    The purpose of this class is to make it easier to understand the layers of the API.
    """

    data: List[dict] | pd.DataFrame | Any
    status: int
    message: str

    class Config:
        arbitrary_types_allowed = True

    def __iter__(self):
        yield self.data
        yield self.status
        yield self.message

class APIOutput(BaseModel):
    """
    Outputs the data, status code, and message of the CRUD operation. All data is
    converted to JSON strings.
    """

    data: str 
    status: int
    message: str

    def __init__(self, data: List[dict] | pd.DataFrame, status: int, message: str):
        data = self.to_json(data)
        super().__init__(data=data, status=status, message=message)

    def to_json(self, data):
        """
        Converts the data content to JSON strings.
        """
        if isinstance(data, pd.DataFrame):
            return data.to_json(orient='records')
        elif isinstance(data, list):
            return json.dumps(data)
        elif hasattr(data, '_asdict'):
            return data.as_json
        return data


class CRUDInsertInput(TableNames, BaseModel):
    data: list

class CRUDSelectInput(TableNames, BaseModel):
    filters: Optional[QueryFilters]
    lambda_args: Optional[QueryArgs]

class CRUDUpdateInput(TableNames, BaseModel):
    data: dict

class CRUDDeleteInput(TableNames, BaseModel):
    field: str
    ids: List[int | str]