from sqlmodel import select, func
from app.models import Category, Unit, Recipe, Ingredient, RecipeIngredient

CATEGORY_QUERY = select(
    Category.id.label('id'),
    Category.name.label('name'),
    Category.type.label('type'),
    Category.created_at.label('created_at'),
    Category.updated_at.label('updated_at'),
).order_by(Category.id)

UNIT_QUERY = select(
    Unit.id.label('id'),
    Unit.name.label('name'),
    Unit.abbreviation.label('abbreviation'),
    Unit.base.label('base'),
    Unit.created_at.label('created_at'),
    Unit.updated_at.label('updated_at'),
).order_by(Unit.id)

RECIPE_QUERY = select(
    Recipe.id.label('id'),
    Recipe.name.label('name'),
    Recipe.description.label('description'),
    Recipe.period.label('period'),
    Recipe.type.label('type'),
    Recipe.created_at.label('created_at'),
    Recipe.updated_at.label('updated_at'),
).order_by(Recipe.id)

INGREDIENT_QUERY = select(
    Ingredient.id.label('id'),
    Ingredient.name.label('name'),
    Ingredient.description.label('description'),
    Ingredient.type.label('type'),
    Ingredient.created_at.label('created_at'),
    Ingredient.updated_at.label('updated_at'),
).order_by(Ingredient.id)


row_number = func.row_number().over(order_by=Ingredient.name)
RECIPE_INGREDIENT_QUERY = select(
    row_number.label('id'),
    RecipeIngredient.id.label('id_recipe_ingredient'),
    Ingredient.id.label('id_ingredient'),
    Ingredient.name.label('name'),
    Ingredient.description.label('description'),
    Ingredient.type.label('type'),
    Ingredient.created_at.label('created_at'),
    Ingredient.updated_at.label('updated_at'),
    RecipeIngredient.quantity.label('quantity'),
    Unit.id.label('id_unit'),
    Unit.name.label('unit'),
).select_from(
    Ingredient
).outerjoin(
    RecipeIngredient, RecipeIngredient.id_ingredient == Ingredient.id
).outerjoin(
    Unit, Unit.id == RecipeIngredient.id_unit
).order_by(Ingredient.name)

RECIPE_INGREDIENT_FILTERED_QUERY = select(
    row_number.label('id'),
    RecipeIngredient.id.label('id_recipe_ingredient'),
    Ingredient.id.label('id_ingredient'),
    Ingredient.name.label('name'),
    Ingredient.description.label('description'),
    Ingredient.type.label('type'),
    Ingredient.created_at.label('created_at'),
    Ingredient.updated_at.label('updated_at'),
    RecipeIngredient.quantity.label('quantity'),
    Unit.id.label('id_unit'),
    Unit.name.label('unit'),
).select_from(
    Ingredient
).outerjoin(
    RecipeIngredient, RecipeIngredient.id_ingredient == Ingredient.id
).outerjoin(
    Unit, Unit.id == RecipeIngredient.id_unit
) # WHERE to be added on the route