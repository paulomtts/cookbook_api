from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional


REGEX_WORDS = r'^[a-zA-Z\s]+$'
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
URL_REGEX = r'^https:\/\/[^\s\/$.?#].[^\s]*$'


class TimestampModel(SQLModel):
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # Note: sqalchemy's .on_conflict_do_update() does not trigger onupdate events 
    # see the post at https://github.com/sqlalchemy/sqlalchemy/discussions/5903#discussioncomment-327672

class UserModel(SQLModel):
    created_by: int
    updated_by: int
    

class Users(TimestampModel, table=True):
    __tablename__ = 'users'

    google_id: Optional[str] = Field(default=None, primary_key=True)
    google_email: str = Field(regex=EMAIL_REGEX)
    google_picture_url: str = Field(regex=URL_REGEX)
    google_access_token: str
    name: str = Field(regex=REGEX_WORDS)
    locale: str = Field(regex=REGEX_WORDS)

class Sessions(TimestampModel, table=True):
    __tablename__ = 'sessions'

    id: Optional[int] = Field(default=None, primary_key=True)
    google_id: str = Field(foreign_key='users.google_id')
    token: str
    user_agent: str
    client_ip: str
    status: str = Field(regex=REGEX_WORDS)

class Categories(TimestampModel, table=True):
    __tablename__ = 'categories'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(regex=REGEX_WORDS)
    type: str = Field(regex=REGEX_WORDS)

class Units(TimestampModel, table=True):
    __tablename__ = 'units'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(regex=REGEX_WORDS)
    abbreviation: str = Field(regex=REGEX_WORDS)
    base: int

class Recipes(TimestampModel, table=True):
    __tablename__ = 'recipes'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(regex=REGEX_WORDS)
    description: str = None
    period: str = Field(regex=REGEX_WORDS)
    type: str = Field(regex=REGEX_WORDS)
    presentation: str = Field(regex=REGEX_WORDS)

class Ingredients(TimestampModel, table=True):
    __tablename__ = 'ingredients'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(regex=REGEX_WORDS)
    description: str = None
    type: str = Field(regex=REGEX_WORDS)

class RecipeIngredients(TimestampModel, table=True):
    __tablename__ = 'recipe_ingredients'

    id: Optional[int] = Field(default=None, primary_key=True)
    id_recipe: int = Field(foreign_key='recipes.id')
    id_ingredient: int = Field(foreign_key='ingredients.id')
    quantity: float
    id_unit: int = Field(foreign_key='units.id')