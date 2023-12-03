from pydantic import BaseModel
from app.core.schemas import DeleteFilters


class CSTSubmitRecipeInput(BaseModel):
    form_data: dict
    insert_rows: list[dict]
    update_rows: list[dict]
    delete_rows: list[dict]


class CSTDeleteRecipeInput(BaseModel):
    recipe: DeleteFilters
    composition: DeleteFilters

