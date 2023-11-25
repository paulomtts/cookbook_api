from fastapi import status
from sqlalchemy import create_engine, select, insert, delete, update, inspect, Column, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError, ProgrammingError

from typing import List, Literal, Union, Callable, Optional, Any
from collections import namedtuple
from pydantic import BaseModel
from logging import Logger

import pandas as pd



class Task(BaseModel):
    """
    Represents a task to be executed.

    Attributes:
        - function (Callable): The function to be executed.
        - args (Optional[List], optional): The arguments to be passed to the function. Defaults to None.
        - mapping_cls (Optional[Any], optional): The mapping class for the task, to help Pandas order a returned dataframe's columns. Defaults to None.
    """

    function: Callable
    args: Optional[List] = None
    mapping_cls: Optional[Any] = None

    def __init__(self, function: Callable, args: Optional[List] = None, mapping_cls: Optional[Any] = None):
        super().__init__(function=function, args=args, mapping_cls=mapping_cls)

        if args is None:
            self.args = []

    def __iter__(self):
        yield self.function
        yield self.args
        yield self.mapping_cls

class Result(BaseModel):
    """
    Represents the result of an operation.

    Attributes:
        - content (List[pd.DataFrame]): The content of the result.
        - status_code (Literal[200, 204, 400, 500, 503]): The status code of the result.
        - client_message (str): The client message associated with the result.
    """

    content: list | pd.DataFrame
    status_code: Literal[200, 204, 400, 500, 503]
    client_message: str

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, content: list, status_code: Literal[200, 204, 400, 500, 503], client_message: str):
        super().__init__(content=content, status_code=status_code, client_message=client_message)

    def __iter__(self):
        yield self.content
        yield self.status_code
        yield self.client_message

class SuccessMessages(BaseModel):
    """
    A dummy class for storing success messages for logging and client response.
    """
    client: Optional[str] = ''
    logger: Optional[str] = ''

    def __init__(self, client: Optional[str] = '', logger: Optional[str] = ''):
        super().__init__(client=client, logger=logger)

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

    , IndexError: ErrorObject(
        status.HTTP_400_BAD_REQUEST
        , "Index error."
        , "Expected returning data but none was found."
    )

    , Exception: ErrorObject(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Internal server error."
        , "An unknown error occurred while interacting with the database."
    )
}

class DBManager():
    """
    A class that manages the database connection and provides methods for executing queries and operations on the database.
    - Note: any returned data will be in the form of a Pandas DataFrame.

    Args:
        - dialect (str): The database dialect.
        - user (str): The username for the database connection.
        - password (str): The password for the database connection.
        - address (str): The address of the database server.
        - port (str): The port number for the database connection.
        - database (str): The name of the database.
        - schema (str): The schema to be used for the database connection.
        - logger (Logger): The logger object for logging messages.

    Attributes:
        - engine (Engine): The SQLAlchemy engine object for the database connection.
        - session (Session): The SQLAlchemy session object for executing database operations.
        - logger (Logger): The logger object for logging messages.

    Methods:
        - query(table_cls, filters=None, messages=None, order_by=None, as_task_list=False): Executes a query on the specified table class with optional filters and ordering.
        - insert(table_cls, data_list, messages=None, returning=True, as_task_list=False): Inserts data into the specified table.
        - update(table_cls, data_list, messages=None, returning=True, as_task_list=False): Updates records in the database table.
        - delete(table_cls, filters, messages=None, returning=True, as_task_list=False): Deletes records from the specified table based on the provided filters.
        - upsert(table_cls, data_list, messages=None, returning=True, as_task_list=False): Attempts to insert data into the specified table, and updates the data if the insert fails because of a unique constraint violation.
        - touch(task_list, messages=None, is_select=False, mapping_cls=None): Executes a series of tasks and returns the result, committing the changes if all tasks are successful.

    Raises:
        - IntegrityError: Raised when there is a violation of a unique constraint or foreign key constraint.
        - ProgrammingError: Raised when there is an error in the SQL statement.
        - OperationalError: Raised when there is an operational error in the database.
        - InternalError: Raised when there is an internal error in the database.
        - ValueError: Raised when there is an invalid value or argument.
        - StaleDataError: Raised when there is a conflict with concurrent updates.
        - IndexError: Raised when there is an index error.
        - Exception: Raised for any other exception.
    """

    def __init__(self, dialect: str, user: str, password: str, address: str, port: str, database: str, schema: str, logger: Logger):
        self.engine = create_engine(f'{dialect}://{user}:{password}@{address}:{port}/{database}', connect_args={"options": f"-csearch_path={schema}"}, pool_pre_ping=True)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.logger = logger


    def __del__(self):
        """
        Automatically close the session and release resources when this object is about to be destroyed.
        """
        try:
            self.session.close()
            self.logger.info(f"Gracefully closed a session.")
        except AttributeError:
            pass  # In case close() method is already called or doesn't exist


    def query(self, table_cls, filters: dict = None, messages: SuccessMessages = None, order_by: List[Column] = None, as_task_list: bool = False):
        """
        Executes a query on the specified table class with optional filters and ordering.

        Args:
            - table_cls (`class`): The table class to query.
            - filters (`list, optional`): A dictionary containing the column names as keys and the values to filter on as values.
            - messages (`Messages, optional`): An object for storing success messages. Defaults to None.
            - order_by (`bool, optional`): A list of columns to order the query by, passed as as <instance>.<column_name>. Defaults to None.
            - as_task_list (`bool, optional`): Whether to avoid immediately executing the task and return it as a callback instead. Defaults to `False`.

        Returns:
            - `Task` or `Result`: `Task` object or a `Result` object containing the query results.
        """

        if filters is None: filters = {}

        conditions = []
        if 'and' in filters:
            and_conditions = [getattr(table_cls, column).in_(values) for column, values in filters['and'].items()]
            conditions.append(and_(*and_conditions))

        if 'or' in filters:
            or_conditions = [getattr(table_cls, column).in_(values) for column, values in filters['or'].items()]
            conditions.append(or_(*or_conditions))


        statement = select(table_cls)


        if conditions:
            statement = statement.where(*conditions)

        if order_by:
            statement = statement.order_by(*order_by)


        fn = lambda statement: self.session.execute(statement)
        task = Task(fn, [statement], mapping_cls=table_cls)

        if as_task_list:
            return task

        return self.touch(task, messages, True)


    def insert(self, table_cls, data_list: List[dict], messages: SuccessMessages = None, returning: bool = True, as_task_list: bool = False):
        """
        Insert data into the specified table.

        Args:
            - table_cls (`Table`): The table class to insert data into.
            - data_list (`List[dict]`): A list of dictionaries representing the data to be inserted.
            - messages (`Messages`, optional): An object for storing success messages. Defaults to `None`.
            - returning (`bool`, optional): Whether to include the inserted data in the result. Defaults to `True`.
            - as_task_list (`bool`, optional): Whether to avoid immediately executing the task and return it as a callback instead. Defaults to `False`.

        Returns:
            - `Task`, `List[Task]` or `Result`: The task or list of tasks representing the insert operation, or a `Result` object containing the inserted data.
        """
        statement = insert(table_cls).values(data_list)

        if returning:
            statement = statement.returning(table_cls)

        fn = lambda statement: self.session.execute(statement)
        task = Task(fn, [statement], mapping_cls=table_cls)

        if as_task_list:
            return task

        return self.touch(task, messages)


    def update(self, table_cls, data_list: List[dict], messages: SuccessMessages = None, returning: bool = True, as_task_list: bool = False):
        """
        Update records in the database table.

        Args:
            - table_cls (`class`): The class representing the database table.
            - data_list (`List[dict]`): A list of dictionaries containing the updated data for each record.
            - messages (`Messages, optional`): An object for storing success messages. Defaults to None.
            - returning `(bool, optional`): Whether to return the updated records. Defaults to True.
            - as_task_list (`bool, optional`): Whether to avoid immediately executing the task and return it as a callback instead. Defaults to `False`.

        Returns:
            - `Union[List[Task], Any]`: If `as_task_list` is True, returns a list of update tasks. Otherwise, returns the result of `self.touch`.
        """

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
                statement = statement.returning(table_cls)

            fn = lambda statement: self.session.execute(statement)
            task = Task(fn, [statement], mapping_cls=table_cls)
            task_list.append(task)
        
        if as_task_list:
            return task_list
        
        return self.touch(task_list, messages)


    def delete(self, table_cls, filters: dict, messages: dict = None, returning: bool = True, as_task_list: bool = False):
        """
        Delete records from the specified table based on the provided filters.

        Args:
            - table_cls (`class`): The table class representing the table to delete records from.
            - filters (`dict`): A dictionary containing the column names as keys and the values to filter on as values.
            - messages (`dict, optional`): A dictionary containing messages to be printed if succesful. Defaults to None.
            - returning (`bool, optional`): Whether to include the deleted records in the return value. Defaults to True.
            - as_task_list (`bool, optional`): Whether to avoid immediately executing the task and return it as a callback instead. Defaults to `False`.

        Returns:
            - `Task` or `list`: The deletion task or a `list` of deletion tasks, depending on the value of `as_task_list`.
        """
        conditions = [getattr(table_cls, column_name).in_(values) for column_name, values in filters.items()]
        statement = delete(table_cls).where(*conditions)
        
        if returning:
            statement = statement.returning(table_cls)

        fn = lambda statement: self.session.execute(statement)
        task = Task(fn, [statement], mapping_cls=table_cls)

        if as_task_list:
            return task

        return self.touch(task, messages)


    def upsert(self, table_cls, data_list: List[dict], messages: SuccessMessages = None, returning: bool = True, as_task_list: bool = False):
        """
        Attempts to insert data into the specified table, and updates the data if the insert fails because of a unique constraint violation.

        Args:
            - table_cls (`class`): The table class.
            - data_list (`List[dict]`): A list of dictionaries containing the data to be upserted.
            - messages (`Messages`, optional): A dictionary containing messages to be printed if succesful. Defaults to None.
            - returning (`bool`, optional): Whether to return the upserted data. Defaults to True.
            - as_task_list (`bool`, optional): Whether to avoid immediately executing the task and return it as a callback instead. Defaults to `False`.

        Returns:
            - `Union[List[Task], Any]`: If `as_task_list` is True, returns a list of Task objects representing the upsert tasks.
            Otherwise, returns the result of the `touch` method.
        """
        task_list = []

        for data in data_list:
            statement = postgres_upsert(table_cls).values(data)\
                        .on_conflict_do_update(index_elements=[table_cls.id], set_=data)\
            
            if returning:
                statement = statement.returning(table_cls)
            
            fn = lambda statement: self.session.execute(statement)
            task = Task(fn, [statement], mapping_cls=table_cls)
            task_list.append(task)

        if as_task_list:
            return task_list

        return self.touch(task_list, messages)


    def touch(self, task_list: Union[Task, List[Task]], messages: SuccessMessages = None, is_select: bool = False, parse: bool = True) -> Result:
        """
        Executes a series of tasks and returns the result, committing the changes if all tasks are successful. Should any of the tasks fail, 
        the changes are rolled back, an error is raised and the according Result object is returned.

        Args:
            - task_list (`Union[Task, List[Task]]`): A single task or a list of tasks to be executed.
            - messages (`Messages, optional`): An object containing messages for logging and client response. Defaults to None.
            - is_select (`bool, optional`): Indicates whether the tasks are select queries. Defaults to False.
            - parse (`bool, optional`): Indicates whether the returned data should be parsed into a Pandas DataFrame. Defaults to True.

        Returns:
            `Result`: The result of the executed tasks.

        Raises:
            - IntegrityError
            - ProgrammingError
            - OperationalError
            - InternalError
            - ValueError
            - StaleDataError
            - IndexError
            - Exception
        """
        if type(task_list) != list: task_list = [task_list]
       
        content_list = []

        client_message = 'Operation successful.'
        if messages and messages.client:
            client_message = messages.client

        try:
            for task in task_list:
                task = task if isinstance(task, list) else [task]

                group_content = []
                for subtask in task:
                    fn, args, mapping_cls = subtask
                    content = fn(*args)

                    if not parse:
                        content_list.append(content)
                        continue

                    parsed_content = []
                    for row in content:
                        dct = dict(row[0])
                        dct.pop('_sa_instance_state', None)
                        parsed_content.append(dct)

                    group_content.extend(parsed_content)

                if not parse:
                    continue

                df = pd.DataFrame(group_content)

                if mapping_cls:
                    mapping_columns = mapping_cls.__annotations__.keys()
                    columns = [*mapping_columns] + [col for col in df.columns if col not in mapping_columns]
                    df = df[columns]

                content_list.append(df)

            if not is_select:
                    self.session.commit()


        except (IntegrityError, ProgrammingError, OperationalError, InternalError, ValueError, StaleDataError, IndexError, Exception) as e:
            self.session.rollback()

            error = ERROR_MAP.get(type(e))
            self.logger.error(f"{error.logger_message} Message:\n\n {e}.\n")

            return Result([], error.status_code, error.client_message)

        if is_select and len(content_list) == 1 and getattr(content_list[0], 'empty', True):
            self.logger.debug(f"Query returned no results.")
            return Result([], STATUS_DICT[204], client_message)
        
        if messages and messages.logger: 
            self.logger.debug(messages.logger)
            
        if len(content_list) == 1:
            return Result(content_list[0], STATUS_DICT[200], client_message)

        return Result(content_list, STATUS_DICT[200], client_message)
    