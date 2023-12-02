from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional


REGEX_WORDS = r'^[a-zA-Z\s]+$'
REGEX_INTEGERS = r'^[0-9]+$'


class TimestampModel(SQLModel):
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # Note: sqalchemy's .on_conflict_do_update() does not trigger onupdate events 
    # see the post at https://github.com/sqlalchemy/sqlalchemy/discussions/5903#discussioncomment-327672

class Categories(TimestampModel, table=True):
    __tablename__ = 'categories'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default=None, regex=REGEX_WORDS)
    type: str = Field(default=None, regex=REGEX_WORDS)

class Units(TimestampModel, table=True):
    __tablename__ = 'units'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default=None, regex=REGEX_WORDS)
    abbreviation: str = Field(default=None, regex=REGEX_WORDS)
    base: int = Field(default=None)

class Recipes(TimestampModel, table=True):
    __tablename__ = 'recipes'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default=None, regex=REGEX_WORDS)
    description: str = Field(default=None)
    period: str = Field(default=None, regex=REGEX_WORDS)
    type: str = Field(default=None, regex=REGEX_WORDS)
    presentation: str = Field(default=None, regex=REGEX_WORDS)

class Ingredients(TimestampModel, table=True):
    __tablename__ = 'ingredients'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default=None, regex=REGEX_WORDS)
    description: str = Field(default=None)
    type: str = Field(default=None, regex=REGEX_WORDS)

class RecipeIngredients(TimestampModel, table=True):
    __tablename__ = 'recipe_ingredients'

    id: Optional[int] = Field(default=None, primary_key=True)
    id_recipe: int = Field(default=None, foreign_key='recipes.id')
    id_ingredient: int = Field(default=None, foreign_key='ingredients.id')
    quantity: float = Field(default=None)
    id_unit: int = Field(default=None, foreign_key='units.id')