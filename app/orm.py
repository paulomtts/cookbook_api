from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import and_
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError, ProgrammingError

import threading
import datetime
from .models import Recipes


STATUS_DICT = {
    200: status.HTTP_200_OK
    , 201: status.HTTP_201_CREATED
    , 204: status.HTTP_204_NO_CONTENT
    , 400: status.HTTP_400_BAD_REQUEST
    , 404: status.HTTP_404_NOT_FOUND
    , 500: status.HTTP_500_INTERNAL_SERVER_ERROR
    , 503: status.HTTP_503_SERVICE_UNAVAILABLE
}

class DBClient():

    def __init__(self, dialect, user, password, address, port, database, schema, logger):
        self.engine = create_engine(f'{dialect}://{user}:{password}@{address}:{port}/{database}', connect_args={"options": f"-csearch_path={schema}"}, pool_pre_ping=True)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.logger = logger

        # self.jobs = {}
        # self.thread = threading.Thread(target=self._manage_jobs)
        # self.thread.daemon = True  # Make the thread a daemon so it doesn't block program exit
        # self.thread.start()


    def insert_dummy_data(self, cls):
        import random
        import string

        # keys = list(cls.__annotations__.keys())

        entries = []
        generate_random_string = lambda length: ''.join(random.choice(string.ascii_letters) for _ in range(length))
        for _ in range(1000):
            recipe = dict(
                name=generate_random_string(10),
                description=generate_random_string(20),
                period=generate_random_string(5),
                type=generate_random_string(5))
            entries.append(recipe)
            messages = {
                'logger': f"DUMMY insert in Recipe was successful."
            }
            
        self.bulk_insert(Recipes, entries, messages)


    def __del__(self):
        """
        Automatically close the session and release resources when the DBClient object is about to be destroyed.
        """
        try:
            self.close()
        except AttributeError:
            pass  # In case close() method is already called or doesn't exist

    def _manage_jobs(self):
        """
        Manage nested jobs' timeouts.
        """
        while True:
            current_time = datetime.datetime.now()  
            keys_to_delete = []

            for job_uuid, job in self.jobs.items():
                start_time = datetime.datetime.strptime(job['start_time'], '%Y-%m-%d %H:%M:%S')

                if current_time - start_time >= datetime.timedelta(seconds=10):
                    keys_to_delete.append(job_uuid)

            for key in keys_to_delete:
                del self.jobs[key]

    def build_job(self, uuid):
        """
        Build and insert a new job.
        """
        new_job = {
            'start_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            , 'tasks': []
        }
        self.jobs[uuid] = new_job
    

    def insert_task(self, uuid, task):
        """
        Insert a task into an existing job.
        """
        job = self.jobs.get(uuid)
        if job:
            job['tasks'].append(task)


    def execute_job(self, uuid, messages: list = None):
        """
        Execute all tasks in a job.
        """
        job = self.jobs.pop(uuid, None)
        if job:
            return self.nested_touch(job['tasks'], messages)


    def insert(self, table_object, messages: dict = None):
        """
        Session-based insert.
        """
        fn = lambda: self.session.merge(table_object)
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


    def delete(self, table_cls, filters: dict, messages: dict = None):
        """
        Session-based delete.
        """
        filter_conditions = [getattr(table_cls, column_name).in_(values) for column_name, values in filters.items()]

        fn = lambda: self.session.query(table_cls).filter(and_(*filter_conditions)).delete(synchronize_session=False)
        result, status_code, message = self.touch(fn, [], messages)
        return result, status_code, message  


    def touch(self, func, args: list = None, messages: dict = None, is_select=False) -> tuple:       
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

            if is_select and not result: # necessary for cases where you want to know that no results were found
                status_code = 204
                client_message = "The resource was found but had no data stored."
                self.logger.warning(f"Table was found but had no rows.")

                return result, status_code, client_message

            if logger_message:
                self.logger.debug(logger_message)

        except IntegrityError as error:
            self.session.rollback()
            status_code = 400
            client_message = "Integrity error."
            self.logger.error(f"Attempted to breach database constraints. Message:\n\n {error}.\n")
        except ProgrammingError as error:
            status_code = 500
            client_message = "Statement error."
            self.logger.error(f"Attempted to perform a bad statement. Message:\n\n {error}.\n")
        except OperationalError as error:
            status_code = 503
            client_message = "Database is unavailable."
            self.logger.error(f"Could not reach the database. Message:\n\n {error}.\n")
        except InternalError as error:
            self.session.rollback()
            status_code = 500
            client_message = "Database error."
            self.logger.error(f"An internal error ocurred in the database. Please contact the dabatase administrator. Message:\n\n {error}.\n")
        except ValueError as error:
            self.session.rollback()
            status_code = 400
            client_message = "Bad request."
            self.logger.warning(f"Incoming data did not pass validation. Message:\n\n {error}.\n")
        except Exception as error:
            self.session.rollback()
            status_code = 500
            client_message = "Internal server error."
            self.logger.error(f"An unknown error occurred while interacting with the database. Message:\n\n {error}.\n")
        finally:
            self.session.close()

        status_code = STATUS_DICT[status_code]
        return result, status_code, client_message
    

    def nested_touch(self, tasks: list, messages: list = None):
        """
        Execute a list of tasks in a nested transaction.
        """

        results_list = []       
        exceptions_occurred = False

        self.session.begin_nested()

        try:
            for id, task in enumerate(tasks):
                result = None
                status_code = 200

                client_message = messages[id].get('client')
                logger_message = messages[id].get('logger')

                result = task()  # Execute the task

                if not result:
                    status_code = 204
                    client_message = "The resource was found but had no data stored."
                    self.logger.warning(f"Table was found but had no rows.")

                if logger_message:
                    self.logger.debug(logger_message)
                
                new_tuple = (result, STATUS_DICT[status_code], client_message)
                results_list.append(new_tuple)

            self.session.commit()

        except IntegrityError as error:
            self.session.rollback()
            status_code = 400
            client_message = "Integrity error."
            self.logger.error(f"Attempted to breach database constraints. Message:\n\n {error}.\n")
            exceptions_occurred = True
        except ProgrammingError as error:
            self.session.rollback()
            status_code = 500
            client_message = "Statement error."
            self.logger.error(f"Attempted to perform a bad statement. Message:\n\n {error}.\n")
            exceptions_occurred = True
        except OperationalError as error:
            self.session.rollback()
            status_code = 503
            client_message = "Database is unavailable."
            self.logger.error(f"Could not reach the database. Message:\n\n {error}.\n")
            exceptions_occurred = True
        except InternalError as error:
            self.session.rollback()
            status_code = 500
            client_message = "Database error."
            self.logger.error(f"An internal error ocurred in the database. Please contact the dabatase administrator. Message:\n\n {error}.\n")
            exceptions_occurred = True
        except ValueError as error:
            self.session.rollback()
            status_code = 400
            client_message = "Bad request."
            self.logger.warning(f"Incoming data did not pass validation. Message:\n\n {error}.\n")
            exceptions_occurred = True
        except Exception as error:
            self.session.rollback()
            status_code = 500
            client_message = "Internal server error."
            self.logger.error(f"An unknown error occurred while interacting with the database. Message:\n\n {error}.\n")
            exceptions_occurred = True
        finally:
            self.session.close()
            if exceptions_occurred:
                return [(None, STATUS_DICT[status_code], client_message)]

        return results_list
