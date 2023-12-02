from app.core.schemas import DeleteData

from pydantic import BaseModel


class RecipeDeleteInput(BaseModel):
    recipe: DeleteData
    composition: DeleteData

class RecipeDeleteOutput(BaseModel):
    recipes: str
    recipe_ingredients: str