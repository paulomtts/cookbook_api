from sqlmodel import select, func, literal, case
from app.models import Categories, Units, Recipes, Ingredients, RecipeIngredients

CATEGORY_QUERY = select(
    Categories.id.label('id'),
    Categories.name.label('name'),
    Categories.type.label('type'),
    Categories.created_at.label('created_at'),
    Categories.updated_at.label('updated_at'),
).order_by(Categories.id)

UNIT_QUERY = select(
    Units.id.label('id'),
    Units.name.label('name'),
    Units.abbreviation.label('abbreviation'),
    Units.base.label('base'),
    Units.created_at.label('created_at'),
    Units.updated_at.label('updated_at'),
).order_by(Units.id)

RECIPE_QUERY = select(
    Recipes.id.label('id'),
    Recipes.name.label('name'),
    Recipes.description.label('description'),
    Recipes.period.label('period'),
    Recipes.type.label('type'),
    Recipes.presentation.label('presentation'),
    Recipes.created_at.label('created_at'),
    Recipes.updated_at.label('updated_at'),
).order_by(Recipes.id)

INGREDIENT_QUERY = select(
    Ingredients.id.label('id'),
    Ingredients.name.label('name'),
    Ingredients.description.label('description'),
    Ingredients.type.label('type'),
    Ingredients.created_at.label('created_at'),
    Ingredients.updated_at.label('updated_at'),
).order_by(Ingredients.id)

RECIPE_INGREDIENT = select(
    RecipeIngredients.id.label('id'),
    RecipeIngredients.id_recipe.label('id_recipe'),
    RecipeIngredients.id_ingredient.label('id_ingredient'),
    RecipeIngredients.id_unit.label('id_unit'),
    RecipeIngredients.quantity.label('quantity'),
    RecipeIngredients.created_at.label('created_at'),
    RecipeIngredients.updated_at.label('updated_at'),
).order_by(RecipeIngredients.id)


# These queries allow for a single table to exhibit all ingredients, including those that are not part of the recipe
# while also allowing for the recipe ingredients to be quantified. The division between three states is necessary
# to allow for state comparisons. One for when no Recipe is selected, another for when a recipe has been clicked,
# and the last to compare updates to the recipe ingredients.

RECIPE_COMPOSITION_EMPTY_QUERY = select(
    Ingredients.id.label('id'),
    literal(None).label('id_recipe_ingredient'),
    literal(None).label('id_recipe'),
    Ingredients.id.label('id_ingredient'),
    Ingredients.name.label('name'),
    Ingredients.description.label('description'),
    Ingredients.type.label('type'),
    literal(0).label('quantity'),
    literal(None).label('id_unit')
).select_from(
    Ingredients
).outerjoin(
    RecipeIngredients, RecipeIngredients.id_ingredient == Ingredients.id
).group_by(
    Ingredients.id
).order_by(Ingredients.name)


RECIPE_COMPOSITION_LOADED_QUERY = lambda id_recipe: select(
    Ingredients.id.label('id'),
    func.MAX(case((RecipeIngredients.id_recipe == id_recipe, RecipeIngredients.id), else_=None)).label('id_recipe_ingredient'),
    literal(id_recipe).label('id_recipe'),
    Ingredients.id.label('id_ingredient'),
    Ingredients.name.label('name'),
    Ingredients.description.label('description'),
    Ingredients.type.label('type'),
    func.COALESCE(func.MAX(case((RecipeIngredients.id_recipe == id_recipe, RecipeIngredients.quantity), else_=None)), 0).label('quantity'),
    func.MAX(case((RecipeIngredients.id_recipe == id_recipe, RecipeIngredients.id_unit), else_=None)).label('id_unit')
).select_from(
    Ingredients
).outerjoin(
        RecipeIngredients, RecipeIngredients.id_ingredient == Ingredients.id
).outerjoin(
        Units, Units.id == RecipeIngredients.id_unit
).group_by(
        Ingredients.id
).order_by(Ingredients.name)


RECIPE_COMPOSITION_SNAPSHOT_QUERY = lambda id_recipe: select(
    Ingredients.id.label('id'),
    RecipeIngredients.id.label('id_recipe_ingredient'),
    RecipeIngredients.id_recipe.label('id_recipe'),
    Ingredients.id.label('id_ingredient'),
    Ingredients.name.label('name'),
    Ingredients.description.label('description'),
    Ingredients.type.label('type'),
    case(
        (RecipeIngredients.id_recipe == id_recipe, RecipeIngredients.quantity),
        else_=0
    ).label('quantity'),
    case(
        (RecipeIngredients.id_recipe == id_recipe, Units.id),
        else_=None
    ).label('id_unit')
).select_from(
    Ingredients
).outerjoin(
    RecipeIngredients, RecipeIngredients.id_ingredient == Ingredients.id
).outerjoin(
    Units, Units.id == RecipeIngredients.id_unit
).where(
    RecipeIngredients.id_recipe == id_recipe, RecipeIngredients.quantity > 0
).order_by(Ingredients.name)