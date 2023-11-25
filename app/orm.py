from fastapi import status
from sqlmodel import and_
from sqlalchemy import create_engine, insert, delete, update, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError, ProgrammingError
from sqlalchemy.orm.exc import StaleDataError
from collections import namedtuple

from pydantic import BaseModel
from typing import List, Dict, Literal, Union, Callable, Optional

class Task(BaseModel):
    function: Callable
    args: Optional[List] = None
    kwargs: Optional[Dict] = None

    def __init__(self, function: Callable, args: Optional[List] = None, kwargs: Optional[Dict] = None):
        super().__init__(function=function, args=args, kwargs=kwargs)

        if args is None:
            self.args = []
        if kwargs is None:
            self.kwargs = {}

    def __iter__(self):
        yield self.function
        yield self.args
        yield self.kwargs

class Result(BaseModel):
    content: list
    status_code: Literal[200, 204, 400, 500, 503]
    client_message: str

    def __init__(self, content: list, status_code: Literal[200, 204, 400, 500, 503], client_message: str):
        super().__init__(content=content, status_code=status_code, client_message=client_message)

    def __iter__(self):
        yield self.content
        yield self.status_code
        yield self.client_message

class Messages(BaseModel):
    client: Optional[str] = ''
    logger: Optional[str] = ''

    def __iter__(self):
        yield self.client
        yield self.logger


STATUS_DICT = {
    200: status.HTTP_200_OK
    , 204: status.HTTP_204_NO_CONTENT
    , 400: status.HTTP_400_BAD_REQUEST
    , 500: status.HTTP_500_INTERNAL_SERVER_ERROR
    , 503: status.HTTP_503_SERVICE_UNAVAILABLE
}

ErrorObject = namedtuple('ErrorObject', ['status_code', 'client_message', 'logger_message'])
ERROR_MAP = {
    IntegrityError: ErrorObject(
        status.HTTP_400_BAD_REQUEST
        , "Integrity error."
        , "Attempted to breach database constraints."
    )
    
    , ProgrammingError: ErrorObject(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Statement error."
        , "Attempted to perform a bad statement."
    )
    
    , OperationalError: ErrorObject(
        status.HTTP_503_SERVICE_UNAVAILABLE
        , "Database is unavailable."
        , "Could not reach the database."
    )
    
    , InternalError: ErrorObject(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Database error."
        , "An internal error ocurred in the database. Please contact the dabatase administrator."
    )
    
    , ValueError: ErrorObject(
        status.HTTP_400_BAD_REQUEST
        , "Bad request."
        , "Incoming data did not pass validation."
    )
    
    , StaleDataError: ErrorObject(
        status.HTTP_400_BAD_REQUEST
        , "Stale data."
        , "One or more rows involved in the operation did could not be found or did not match the expected values."
    )

    , Exception: ErrorObject(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Internal server error."
        , "An unknown error occurred while interacting with the database."
    )
}

class DBManager():

    def __init__(self, dialect, user, password, address, port, database, schema, logger):
        self.engine = create_engine(f'{dialect}://{user}:{password}@{address}:{port}/{database}', connect_args={"options": f"-csearch_path={schema}"}, pool_pre_ping=True)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.logger = logger


    def __del__(self):
        """
        Automatically close the session and release resources when the DBClient object is about to be destroyed.
        """
        try:
            self.session.rollback() # ATTENTION: not yet tested
            self.logger.info(f"Uncommitted changes were rolled back.")
            self.session.close()
        except AttributeError:
            pass  # In case close() method is already called or doesn't exist


    def query(self, table_cls, filters: list = None, messages: Messages = None, order_by = None):
        """
        Query and returns rows from a table. If no filters are passed, all rows are returned.
        """
        if filters is None: filters = []

        if order_by:
            fn = lambda filters: self.session.query(table_cls).filter(and_(*filters)).all()
            task = Task(fn, [filters])
        else:
            fn = lambda filters, order_by: self.session.query(table_cls).filter(and_(*filters)).order_by(order_by).all()
            task = Task(fn, [filters, order_by])

        return self.touch(task, messages, True)


    def insert(self, table_cls, data_list: List[dict], messages: Messages = None, returning: bool = True):
        """
        Insert a list of dictionaries as rows in a table.
        """
        statement = insert(table_cls).values(data_list)

        if returning:
            statement = statement.returning(table_cls.__table__.columns)

        fn = lambda statement: self.session.execute(statement)
        task = Task(fn, [statement])

        return self.touch(task, messages, no_parse=(not returning))


    def update(self, table_cls, data_list: List[dict], messages: Messages = None, returning: bool = True):

        assert isinstance(data_list, list), f"Data must be type <list>. Instead, it is type <{type(data_list).__name__}>."

        inspector = inspect(table_cls)
        pk_columns = [column.name for column in inspector.primary_key]  

        task_list = []
        for data in data_list:

            conditions = [getattr(table_cls, pk) == data[pk] for pk in pk_columns]
            statement = (
                update(table_cls)
                .where(*conditions)
                .values(data)
                
            )

            if returning:
                statement = statement.returning(table_cls.__table__.columns)

            fn = lambda statement: self.session.execute(statement)
            task = Task(fn, [statement])
            task_list.append(task)
        
        return self.touch(task_list, messages, no_parse=(not returning))


    def delete(self, table_cls, filters: dict, messages: dict = None, returning: bool = True):
        """
        Delete a list of ORM objects. This method uses Postgres' RETURNING clause to return the deleted objects.
        """
        conditions = [getattr(table_cls, column_name).in_(values) for column_name, values in filters.items()]
        statement = delete(table_cls).where(*conditions)
        
        if returning:
            statement = statement.returning(table_cls.__table__.columns)

        fn = lambda statement: self.session.execute(statement)
        task = Task(fn, [statement])

        return self.touch(task, messages, no_parse=(not returning))


    def upsert(self, table_cls, data_list: List[dict], messages: Messages = None, returning: bool = True):
        """
        Attempt to insert a list of dictionaries as rows into a table. If there is 
        a conflict with the primary key, update them instead. This method uses 
        Postgres' ON CONFLICT clause to perform the upsert.
        """

        assert isinstance(data_list, list), f"Data must be type <list>. Instead, it is type <{type(data_list).__name__}>."

        task_list = []

        for data in data_list:
            statement = postgres_upsert(table_cls).values(data)\
                        .on_conflict_do_update(index_elements=[table_cls.id], set_=data)\
            
            if returning:
                statement = statement.returning(table_cls.__table__.columns)
                        
            
            fn = lambda statement: self.session.execute(statement)
            task = Task(fn, [statement])
            task_list.append(task)

        return self.touch(task_list, messages, no_parse=(not returning))


    def touch(self, task_list: Union[Task, List[Task]], messages: Messages = None, is_select=False, no_parse = False) -> Result:
        """
        Perform a single transaction. This method is used to wrap all CRUD operations.
        Autocommit is enabled by default, but can be disabled by setting commit=False.
        * Note: only disable commit when you are sure that you will commit the changes later.
        This method returns a tuple containing the result, status code and client message,
        or a list of tuples if multiple functions are passed.
        """

        # assert (messages is None or isinstance(messages, Messages)), "Messages must be None or a namedtuple containing 'client' and 'logger' messages."
        if type(task_list) != list: task_list = [task_list]
        
        content = []

        client_message = 'Operation successful.'
        if messages and messages.client:
            client_message = messages.client

        try:
            for task in task_list:

                fn, args, kwargs = task
                value = fn(*args, **kwargs)

                if len(task_list) == 1 and is_select and getattr(value, 'empty', True): # getattr: allow non-Pandas queries
                    self.logger.warning(f"Table was found but had no rows.")
                    return [], STATUS_DICT[204], "The resource was found but had no data stored."

                if messages and messages.logger: 
                    self.logger.debug(messages.logger)

                content.append(value)

            if not is_select:
                self.session.commit()

        except (IntegrityError, ProgrammingError, OperationalError, InternalError, ValueError, StaleDataError, Exception) as e:
            self.session.rollback()

            error = ERROR_MAP.get(type(e))
            self.logger.error(f"{error.logger_message} Message:\n\n {e}.\n")

            return Result([], error.status_code, error.client_message)
        
        if no_parse:
            return Result([], STATUS_DICT[200], client_message)

        parsed_content = self._parse_returning(content)
        return Result(parsed_content, STATUS_DICT[200], client_message)
    

    def _parse_returning(self, content: list):
        """
        Parse the result of a query with a RETURNING clause.
        """
        assert isinstance(content, list), f"Content must be type <list>. Instead, it is type <{type(content).__name__}>."

        parsed_content = []
        for row in content:
            keys = [key for key in row.keys()]
            values = [str(value) for value in row.fetchall()[0]]

            parsed_content.append(dict(zip(keys, values)))

        return parsed_content