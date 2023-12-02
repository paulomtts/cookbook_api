from fastapi import status
from sqlalchemy import create_engine, inspect, select, insert, delete, update, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError, ProgrammingError
from sqlalchemy.sql.selectable import Select

from collections import namedtuple
from datetime import datetime
from typing import List, Any
from logging import Logger

import pandas as pd
import json


SuccessMessages = namedtuple('SuccessMessages', ['client', 'logger'], defaults=['Operation was successful.', None])
ErrorObject = namedtuple('ErrorObject', ['status_code', 'client_message', 'logger_message'])


STATUS_MAP = {
    200: status.HTTP_200_OK
    , 204: status.HTTP_204_NO_CONTENT
    , 400: status.HTTP_400_BAD_REQUEST
    , 500: status.HTTP_500_INTERNAL_SERVER_ERROR
    , 503: status.HTTP_503_SERVICE_UNAVAILABLE
}

ERROR_MAP = {
    IntegrityError: ErrorObject(
        STATUS_MAP[400]
        , "Integrity error."
        , "Attempted to breach database constraints."
    )
    
    , ProgrammingError: ErrorObject(
        STATUS_MAP[500]
        , "Statement error."
        , "Attempted to perform a bad statement."
    )
    
    , OperationalError: ErrorObject(
        STATUS_MAP[503]
        , "Database is unavailable."
        , "Could not reach the database."
    )
    
    , InternalError: ErrorObject(
        STATUS_MAP[500]
        , "Database error."
        , "An internal error ocurred in the database. Please contact the dabatase administrator."
    )
    
    , ValueError: ErrorObject(
        STATUS_MAP[400]
        , "Bad request."
        , "Incoming data did not pass validation."
    )
    
    , StaleDataError: ErrorObject(
        STATUS_MAP[400]
        , "Stale data."
        , "One or more rows involved in the operation did could not be found or did not match the expected values."
    )

    , IndexError: ErrorObject(
        STATUS_MAP[400]
        , "Index error."
        , "Expected returning data but none was found."
    )

    , Exception: ErrorObject(
        STATUS_MAP[500]
        , "Internal server error."
        , "An unknown error occurred while interacting with the database."
    )
}


class DBManager():
    """
    A class that manages the database connection and provides methods for executing queries and manipulating data using
    SQLAlchemy ORM. Note that all methods are capable of bulk operations and returnings in the form of
    either a DataFrame or a namedtuple, the latter meant for providing an object whose properties can be accessed during
    chained operations.

    Args:
        - dialect (str): The database dialect.
        - user (str): The username for the database connection.
        - password (str): The password for the database connection.
        - address (str): The address of the database server.
        - port (str): The port number for the database connection.
        - database (str): The name of the database.
        - schema (str): The schema to be used for the database connection.
        - logger (Logger): The logger object for logging.

    Attributes:
        - engine: The database engine object.
        - session: The database session object.
        - logger: The logger object for logging.

    Methods:
        - __init__: Initializes the DBManager object.
        - __del__: Closes the session and releases resources when the object is destroyed.
        - _map_dataframe: Maps a dataframe to the specified mapping class.
        - current_datetime: Returns the current datetime in the database.
        - parse_returnings: Parses the returnings from a database query and returns the result as a pandas DataFrame.
        - query: Executes a query on the specified table class with optional filters and ordering.
        - insert: Inserts data into the specified table.
        - update: Updates records in the specified table with the given data.
        - delete: Deletes records from the specified table based on the given filters.
        - upsert: Attempts to insert data into the specified table and updates the data if the insert fails due to a unique constraint violation.
        - catching: Decorator that executes a function, commits the session and handles exceptions gracefully.
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
            self.logger.info(f"Could not find a session to close. Gracefully exiting.")


    def _map_dataframe(self, df: pd.DataFrame, mapping_cls: Any):
        """
        Maps a dataframe to the specified mapping class.

        Args:
            - df (`pd.DataFrame`): The dataframe to be mapped.
            - mapping_cls (`Any`): The mapping class for the task, to help Pandas order a returned dataframe's columns.

        Returns:
            - `pd.DataFrame`: The mapped dataframe.
        """
        if df.empty:
            return df

        mapping_columns = mapping_cls.__annotations__.keys()
        columns = [*mapping_columns] + [col for col in df.columns if col not in mapping_columns]
        df = df[columns]

        if 'created_at' in df.columns: df['created_at'] = df['created_at'].astype(str)
        if 'updated_at' in df.columns: df['updated_at'] = df['updated_at'].astype(str)

        return df
    

    def _parse_returnings(self, returnings: List, mapping_cls: Any = None):
        """
        Parses the returnings from a database query and returns the result as a pandas DataFrame.

        Args:
            - returnings (List): The list of returnings from the database query.
            - as_dict (bool, optional): Flag indicating whether to return the result as a dictionary or not. Defaults to False.
            - mapping_cls (Any, optional): The mapping class to be used for mapping the DataFrame. Defaults to None.

        Returns:
            - pd.DataFrame: The parsed result as a pandas DataFrame.
        """

        def to_dict(row):
            dct = dict(row[0])
            dct.pop('_sa_instance_state', None)
            return dct
        
        rows_as_dicts = list(map(to_dict, returnings))

        return self._map_dataframe(pd.DataFrame(rows_as_dicts), mapping_cls)
   

    def _single(self, table_cls, df: pd.DataFrame):
        """
        Returns the first record from a DataFrame as a dictionary.

        Args:
            - df (pd.DataFrame): The DataFrame containing the record to be returned.

        Returns:
            - The record as a dictionary.
        """
        dct = df.to_dict(orient='records')[0]
        json_data = json.dumps(dct)
        tuple_cls = namedtuple(table_cls.__tablename__.capitalize(), list(dct.keys()) + ['as_json'])
        
        return tuple_cls(**dct, as_json=json_data)
    

    def query(self, table_cls, statement: Select = None, filters: dict = None, order_by: List[str] = None, single: bool = None):
        """
        Executes a database query based on the provided parameters. Accepts either a table class or a select statement. If
        a statement is provided, filters and order_by are ignored.

        Args:
            - table_cls (class): The SQLAlchemy table class to query from.
            - statement (Select, optional): The SQLAlchemy select statement to use for the query. Defaults to None.
            - filters (dict, optional): The filters to apply to the query. Defaults to None.
            - order_by (List[str], optional): The columns to order the query results by. Defaults to None.
            - single (bool, optional): Whether to return a single result or a DataFrame. Defaults to None.

        Returns:
            - pandas.DataFrame or namedtuple: If single is False, returns a DataFrame containing the updated records.
            - If `single` is `True`, a `namedtuple` representing the first updated record.
        """

        if table_cls is None and statement is None:
            raise ValueError("Either table_cls or statement must be specified.")
        if table_cls is not None and statement is not None:
            raise ValueError("Only one of table_cls or statement can be specified.")

        if table_cls:
            if filters is None:
                filters = {}

            conditions = []

            if 'and' in filters:
                and_conditions = [getattr(table_cls, column).in_(values) for column, values in filters['and'].items()]
                conditions.append(and_(*and_conditions))

            if 'or' in filters:
                or_conditions = [getattr(table_cls, column).in_(values) for column, values in filters['or'].items()]
                conditions.append(or_(*or_conditions))

            if 'like' in filters:
                like_conditions = [getattr(table_cls, attr).like(val) for attr, values in filters['like'].items() for val in values]
                conditions.append(or_(*like_conditions))

            if 'not_like' in filters:
                not_like_conditions = [getattr(table_cls, attr).notlike(val) for attr, values in filters['not_like'].items() for val in values]
                conditions.append(and_(*not_like_conditions))

            statement = select(table_cls)

            if conditions:
                statement = statement.where(and_(*conditions))

            if order_by:
                order_by_columns = [getattr(table_cls, column) for column in order_by]
                statement = statement.order_by(*order_by_columns)

        df = pd.read_sql(statement, self.engine)

        if 'created_at' in df.columns: df['created_at'] = df['created_at'].astype(str)
        if 'updated_at' in df.columns: df['updated_at'] = df['updated_at'].astype(str)

        if single:
            return self._single(table_cls, df)

        return df


    def insert(self, table_cls, data_list: List[dict], single: bool = False):
        """
        Insert data into the specified table.

        Args:
            - table_cls (class): The table class to insert data into.
            - data_list (List[dict]): A list of dictionaries representing the data to be inserted.
            - single (bool, optional): Whether to return a single row or a DataFrame. Defaults to False.

        Returns:
            - pandas.DataFrame or namedtuple: If single is False, returns a DataFrame containing the updated records.
            - If `single` is `True`, a `namedtuple` representing the first updated record.
        """
        statement = insert(table_cls).values(data_list).returning(table_cls)

        returnings = self.session.execute(statement)
        df = self._parse_returnings(returnings, mapping_cls=table_cls)

        if single:
            return self._single(table_cls, df)

        return df


    def update(self, table_cls, data_list: List[dict], single: bool = False):
        """
        Update records in the specified table with the given data.

        Args:
            - table_cls (class): The table class representing the table to update.
            - data_list (List[dict]): A list of dictionaries containing the data to update.
            - single (bool, optional): If True, only the first updated record will be returned. 
                                    Defaults to False.

        Returns:
            - pandas.DataFrame or namedtuple: If single is False, returns a DataFrame containing the updated records.
            - If `single` is `True`, a `namedtuple` representing the first updated record.
        """
        inspector = inspect(table_cls)
        pk_columns = [column.name for column in inspector.primary_key]  

        results = []
        for data in data_list:
            if data.get('created_at') == '': # reason: ensure that the created_at column is not updated
                data.pop('created_at')

            conditions = [getattr(table_cls, pk) == data[pk] for pk in pk_columns]
            statement = update(table_cls).where(*conditions).values(data).returning(table_cls)

            returnings = self.session.execute(statement)
            results.extend(returnings)

        df = self._parse_returnings(results, mapping_cls=table_cls)

        if single:
            return self._single(table_cls, df)

        return df


    def delete(self, table_cls, filters: dict, single: bool = False):
        """
        Delete records from the specified table based on the given filters.

        Args:
            - table_cls (class): The table class representing the table to delete from.
            - filters (dict): A dictionary containing the column names as keys and the values to filter on as values.
            - single (bool, optional): If True, return a single record as a named tuple. Defaults to False.

        Returns:
            - pandas.DataFrame or namedtuple: If single is False, returns a DataFrame containing the deleted records.
            - If `single` is `True`, a `namedtuple` representing the first deleted record.
        """
        conditions = [getattr(table_cls, column_name).in_(values) for column_name, values in filters.items()]
        statement = delete(table_cls).where(*conditions).returning(table_cls)

        returnings = self.session.execute(statement)
        df = self._parse_returnings(returnings, mapping_cls=table_cls)

        if single:
            return self._single(table_cls, df)

        return df


    def upsert(self, table_cls, data_list: List[dict], single: bool = False):
        """
        Attempts to insert data into the specified table, and updates the data if the insert fails because of a unique constraint violation.

        Args:
            - table_cls (`class`): The table class to insert data into.
            - data_list (`List[dict]`): A list of dictionaries representing the data to be inserted.

        Returns:
            - A `pd.DataFrame` containing the inserted data.
            - If `single` is `True`, a `namedtuple` representing the first inserted record.
        """
        results = []

        for data in data_list:

            if data.get('created_at') == '': # reason: see comment in TimestampModel in models.py
                data.pop('created_at')
            data['updated_at'] = datetime.utcnow()
            
            statement = postgres_upsert(table_cls).values(data)\
                        .on_conflict_do_update(index_elements=[table_cls.id], set_=data)\
                        .returning(table_cls)
            
            returnings = self.session.execute(statement)
            results.extend(returnings)

        df = self._parse_returnings(results, mapping_cls=table_cls)

        if single:
            return self._single(table_cls, df)
        
        return df


    def catching(self, messages: SuccessMessages = None):
            """
            Decorator that catches specific exceptions and handles them gracefully. Note: does not commit.

            How to declare:
                - Place decorator above function like so:\n
                >>> @instace.catching()
                    def fn():
            
            Args:
                - session: The database session.
                - logger: The logger.

            Returns:
                - callable: The decorated function.
            """
            def decorator(func):
                def wrapper(*args, **kwargs):
                    try:
                        content = func(*args, **kwargs)
                        self.session.commit()

                        if messages and messages.logger:
                            self.logger.info(messages.logger)

                        return content, STATUS_MAP[200], messages.client if messages else 'Operation was successful.'
                    except tuple(ERROR_MAP.keys()) as e:
                        self.session.rollback()

                        error = ERROR_MAP.get(type(e), ERROR_MAP[Exception])
                        self.logger.error(f"{error.logger_message} \nMethod: <{func.__name__}>\t\tMessage:\n\n {e}.\n")

                        return [], error.status_code, error.client_message
                return wrapper
            return decorator