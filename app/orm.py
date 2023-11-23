from fastapi import status
from sqlmodel import and_
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError, ProgrammingError

from collections import namedtuple

            
STATUS_DICT = {
    200: status.HTTP_200_OK
    , 204: status.HTTP_204_NO_CONTENT
    , 400: status.HTTP_400_BAD_REQUEST
    , 500: status.HTTP_500_INTERNAL_SERVER_ERROR
    , 503: status.HTTP_503_SERVICE_UNAVAILABLE
}

Error = namedtuple('ErrorObject', ['status_code', 'client_message', 'logger_message'])
ERROR_MAP = {
    IntegrityError: Error(
        status.HTTP_400_BAD_REQUEST
        , "Integrity error."
        , "Attempted to breach database constraints."
    )
    
    , ProgrammingError: Error(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Statement error."
        , "Attempted to perform a bad statement."
    )
    
    , OperationalError: Error(
        status.HTTP_503_SERVICE_UNAVAILABLE
        , "Database is unavailable."
        , "Could not reach the database."
    )
    
    , InternalError: Error(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Database error."
        , "An internal error ocurred in the database. Please contact the dabatase administrator."
    )
    
    , ValueError: Error(
        status.HTTP_400_BAD_REQUEST
        , "Bad request."
        , "Incoming data did not pass validation."
    )
    
    , Exception: Error(
        status.HTTP_500_INTERNAL_SERVER_ERROR
        , "Internal server error."
        , "An unknown error occurred while interacting with the database."
    )
}

class DBClient():

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


    def insert(self, table_object, messages: dict = None, merge = True):
        """
        Single insert. This uses .add() by default, but can be 
        changed to .merge() by setting merge=True.
        """

        if hasattr(table_object, 'updated_at'):
            delattr(table_object, 'updated_at') # reason: update this timestamp

        if merge:
            fn = lambda: self.session.merge(table_object)
        else:
            fn = lambda: self.session.add(table_object)
        
        return self.touch(fn, messages)    


    def bulk_insert(self, table_cls, data_list, messages: dict = None):
        """
        Bulk insert.
        """
        fn = lambda: self.session.bulk_insert_mappings(table_cls, data_list)
        return self.touch(fn, messages)

    
    def query(self, table_cls, filters: list = None, messages: dict = None, order_by = None):
        """
        Query and return a list of ORM objects.
        """
        if filters is None: filters = []

        if order_by:
            fn = lambda: self.session.query(table_cls).filter(and_(*filters)).all()
        else:
            fn = lambda: self.session.query(table_cls).filter(and_(*filters)).order_by(order_by).all()
        
        result, status_code, message = self.touch(fn, messages, True)

        return result, status_code, message


    def update(self, table_cls, filters: list, attributes: dict, messages: dict = None):
        """
        Single update.
        """

        fn = lambda: self.session.query(table_cls).filter(and_(*filters)).update(attributes)
        result, status_code, message = self.touch(fn, messages)
        return result, status_code, message


    def bulk_update(self, table_cls, data_list, messages: dict = None):
        """
        Bulk update.
        """
        fn = lambda: self.session.bulk_update_mappings(table_cls, data_list)
        return self.touch(fn, messages)



    # def upsert(self, table_cls, data_list, messages: dict = None):
    #     """
    #     Insert or update a list of ORM objects, depending on whether they already exist.
    #     This method uses Postgres' RETURNING clause to return the inserted/updated objects.
    #     """

    #     statement = postgres_upsert(table_cls).values(data_list)
    #     statement = statement.on_conflict_do_update(index_elements=[table_cls.id])
    #     statement = statement.returning(table_cls)

    #     fn = lambda: self.session.execute(statement)
    #     return self.touch(fn, messages)
    
    # # https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html#orm-queryguide-upsert

    def delete(self, table_cls, filters: dict, messages: dict = None):
        """
        Session-based delete.
        """
        filter_conditions = [getattr(table_cls, column_name).in_(values) for column_name, values in filters.items()]

        fn = lambda: self.session.query(table_cls).filter(and_(*filter_conditions)).delete(synchronize_session=False)
        result, status_code, message = self.touch(fn, messages)
        return result, status_code, message  


    def touch(self, func_list: list, messages: dict = None, is_select=False) -> tuple:
        """
        Perform a single transaction. This method is used to wrap all CRUD operations.
        Autocommit is enabled by default, but can be disabled by setting commit=False.
        * Note: only disable commit when you are sure that you will commit the changes later.
        """

        if messages is None: messages = {}
        if type(func_list) != list: func_list = [func_list]
        
        client_message = messages.get('client')
        logger_message = messages.get('logger')

        Result = namedtuple('Result', ['value', 'status_code', 'client_message'])

        result_list = []
        status_code = STATUS_DICT[200]

        try:
            for func in func_list:

                value = func()
                result = Result(value, STATUS_DICT[200], client_message)

                if is_select and getattr(value, 'empty', True):
                    result = Result([], STATUS_DICT[204], "The resource was found but had no data stored.")
                    self.logger.warning(f"Table was found but had no rows.")

                    return result, status_code, client_message

                if logger_message: 
                    self.logger.debug(logger_message)

                result_list.append(result)

            if not is_select:
                self.session.commit()

        except (IntegrityError, ProgrammingError, OperationalError, InternalError, ValueError, Exception) as e:
            self.session.rollback()

            error = ERROR_MAP.get(type(e))
            self.logger.error(f"{error.logger_message} Message:\n\n {e}.\n")

            return Result(None, STATUS_DICT[error.status_code], error.client_message)
        
        if len(result_list) == 1:
            result_list = result_list[0]

        return result_list