from sqlmodel import select, func, literal
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

RECIPE_INGREDIENT = select(
    RecipeIngredient.id.label('id'),
    RecipeIngredient.id_recipe.label('id_recipe'),
    RecipeIngredient.id_ingredient.label('id_ingredient'),
    RecipeIngredient.id_unit.label('id_unit'),
    RecipeIngredient.quantity.label('quantity'),
    RecipeIngredient.created_at.label('created_at'),
    RecipeIngredient.updated_at.label('updated_at'),
).order_by(RecipeIngredient.id)


# These queries allow for a single table to exhibit all ingredients, including those that are not part of the recipe
# while also allowing for the recipe ingredients to be quantified. The division between three states is necessary
# to allow for state comparisons. One for when no Recipe is selected, another for when a recipe has been clicked,
# and the last to compare updates to the recipe ingredients.
row_number = func.row_number().over(order_by=Ingredient.name)
RECIPE_COMPOSITION_INITIAL_STATE_QUERY = select(
    row_number.label('id'),
    RecipeIngredient.id.label('id_recipe_ingredient'),
    Ingredient.id.label('id_ingredient'),
    Ingredient.name.label('name'),
    Ingredient.description.label('description'),
    Ingredient.type.label('type'),
    Ingredient.created_at.label('created_at'),
    Ingredient.updated_at.label('updated_at'),
    literal(0).label('quantity'),
    Unit.id.label('id_unit'),
    Unit.name.label('unit'),
).select_from(
    Ingredient
).outerjoin(
    RecipeIngredient, RecipeIngredient.id_ingredient == Ingredient.id
).outerjoin(
    Unit, Unit.id == RecipeIngredient.id_unit
).order_by(Ingredient.name)

row_number = func.row_number().over(order_by=Ingredient.name)
RECIPE_COMPOSITION_LOADED_STATE_QUERY = select(
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

RECIPE_COMPOSITION_FILTERED_STATE_QUERY = lambda id: select(
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
).where(
    RecipeIngredient.id_recipe == id
).order_by(Ingredient.name)