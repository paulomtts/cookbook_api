from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import and_
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError, ProgrammingError

from app.queue import JobQueue
from collections import namedtuple
from uuid import uuid4

            
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
        self.queue = JobQueue()


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
        Session-based insert.
        """
        if hasattr(table_object, 'updated_at'):
            delattr(table_object, 'updated_at') # reason: update this timestamp

        if merge:
            fn = lambda: self.session.merge(table_object)
        else:
            fn = lambda: self.session.add(table_object)
        result, status_code, message = self.touch(fn, [], messages)
        return result, status_code, message


    def bulk_insert(self, table_cls, data_list, messages: dict = None):
        """
        Session-based bulk insert.
        """
        fn = lambda: self.session.bulk_insert_mappings(table_cls, data_list)
        result, status_code, message = self.touch(fn, [], messages)
        return result, status_code, message
    

    def query(self, table_cls, filters: list = None, messages: dict = None, order_by = None):
        """
        Session-based query. Returns a list of ORM objects.
        """
        if filters is None: filters = []

        if order_by:
            fn = lambda: self.session.query(table_cls).filter(and_(*filters)).all()
        else:
            fn = lambda: self.session.query(table_cls).filter(and_(*filters)).order_by(order_by).all()
        result, status_code, message = self.touch(fn, [], messages, True)

        if type(result) == list and len(result) == 1:
            result = result[0]

        return result, status_code, message


    def update(self, table_cls, filters: list, attributes: dict, messages: dict = None):
        """
        Session-based update.
        """

        fn = lambda: self.session.query(table_cls).filter(and_(*filters)).update(attributes)
        result, status_code, message = self.touch(fn, [], messages)
        return result, status_code, message


    def bulk_update(self, table_cls, pairings: list[tuple], messages: dict = None):
        """
        Session-based update. Note: This uses nested transactions.
        """

        uuid = uuid4()
        self.build_job(uuid)

        for filters, attributes in pairings:
            fn = lambda: self.session.query(table_cls).filter(and_(*filters)).update(attributes)
            self.insert_task(uuid, fn, messages)

        job_results = self.execute_job(uuid) 

        if type(job_results) != list:
            return job_results.result, job_results.status_code, job_results.client_message
        else:
            return [job.result for job in job_results], status.HTTP_200_OK, "Bulk update was succesful."


    def delete(self, table_cls, filters: dict, messages: dict = None):
        """
        Session-based delete.
        """
        filter_conditions = [getattr(table_cls, column_name).in_(values) for column_name, values in filters.items()]

        fn = lambda: self.session.query(table_cls).filter(and_(*filter_conditions)).delete(synchronize_session=False)
        result, status_code, message = self.touch(fn, [], messages)
        return result, status_code, message  


    def touch(self, func, args: list = None, messages: dict = None, is_select=False) -> tuple:
        """
        Perform a single transaction. This method is used to wrap all CRUD operations.
        Autocommit is enabled by default, but can be disabled by setting commit=False.
        * Note: only disable commit when you are sure that you will commit the changes later.

        """

        if args is None: args = [] # reason: https://stackoverflow.com/questions/1132941/least-astonishment-and-the-mutable-default-argument
        if messages is None: messages = {}
        
        client_message = messages.get('client')
        logger_message = messages.get('logger')

        result = None
        status_code = 200

        try:
            result = func(*args)

            if not is_select:
                self.session.commit()

            if is_select and getattr(result, 'empty', True): # necessary for cases where you want to know that no results were found
                status_code = 204
                client_message = "The resource was found but had no data stored."
                self.logger.warning(f"Table was found but had no rows.")

                return result, status_code, client_message

            if logger_message:
                self.logger.debug(logger_message)

        except (IntegrityError, ProgrammingError, OperationalError, InternalError, ValueError, Exception) as error:
            self.session.rollback()

            error_tuple = ERROR_MAP.get(type(error))

            status_code = error_tuple.status_code
            client_message = error_tuple.client_message
            logger_message = error_tuple.logger_message

            self.logger.error(f"{logger_message} Message:\n\n {error}.\n")

        status_code = STATUS_DICT[status_code]
        return result, status_code, client_message
    

    def multi_touch(self, task_list: list) -> tuple:
        """
        Execute a list of tasks and commit them all at once. If any of 
        the tasks fail, the entire transaction is rolled back.
        """

        JobResult = namedtuple('JobResult', ['result', 'status_code', 'client_message'])
        results_list = []       
        exceptions_occurred = False

        try:
            for task in task_list:
                status_code = 200

                result = task()  # Execute the task
                
                new_tuple = JobResult(result, STATUS_DICT[status_code], None)
                results_list.append(new_tuple)

            self.session.commit()

        except (IntegrityError, ProgrammingError, OperationalError, InternalError, ValueError, Exception) as error:
            self.session.rollback()

            error_tuple = ERROR_MAP.get(type(error))

            status_code = error_tuple.status_code
            client_message = error_tuple.client_message
            logger_message = error_tuple.logger_message

            self.logger.error(f"{logger_message} Message:\n\n {error}.\n")
            exceptions_occurred = True
        finally:
            if exceptions_occurred:
                client_message = client_message + " Some tasks failed. No changes were persisted."
                return JobResult(None, STATUS_DICT[status_code], client_message)
                

        return results_list
