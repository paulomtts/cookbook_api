from sqlmodel import Field, SQLModel, BigInteger, Column
from datetime import datetime
from typing import Optional


REGEX_WORDS = r'^[a-zA-Z\s]+$'
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
JWT_REGEX = r'^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_.+/=]+$' 
URL_REGEX = r'^https:\/\/[^\s\/$.?#].[^\s]*$'


class TimestampModel(SQLModel):
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # Note: sqalchemy's .on_conflict_do_update() does not trigger onupdate events 
    # see the post at https://github.com/sqlalchemy/sqlalchemy/discussions/5903#discussioncomment-327672


#######################################################
class UserModel(SQLModel):
    created_by: int
    updated_by: int

# CREATE TABLE users (
#     id SERIAL PRIMARY KEY
#     , google_id BIGINT NOT NULL
#     , google_email VARCHAR(45) NOT NULL
#     , name VARCHAR(45) NOT NULL
#     , locale VARCHAR(8) NOT NULL
#     , created_at TIMESTAMP DEFAULT NOW()
#     , updated_at TIMESTAMP DEFAULT NOW()
# );

class Users(TimestampModel, table=True):
    __tablename__ = 'users'

    id: Optional[int] = Field(default=None, primary_key=True)
    google_id: int = Field(sa_column=Column(BigInteger()))
    google_email: str = Field(regex=EMAIL_REGEX)
    google_picture_url: str = Field(regex=URL_REGEX)
    name: str = Field(regex=REGEX_WORDS)
    locale: str = Field(regex=REGEX_WORDS)


class Sessions(TimestampModel, table=True):
    __tablename__ = 'sessions'

    id: Optional[int] = Field(default=None, primary_key=True)
    id_user: int
    jwt: str = Field(regex=JWT_REGEX)
    google_access_token: str = Field(regex=JWT_REGEX)
    status: str = Field(regex=REGEX_WORDS)
#######################################################


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