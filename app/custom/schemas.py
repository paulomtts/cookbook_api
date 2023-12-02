from pydantic import BaseModel

class CSTDeleteData(BaseModel):
    field: str
    values: list[str | int]


class CSTSubmitRecipeInput(BaseModel):
    recipe: CSTDeleteData
    composition: CSTDeleteData


class CSTDeleteRecipeInput(BaseModel):
    recipes: str
    recipe_ingredients: str