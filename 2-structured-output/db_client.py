# Connect to the SQLite database
import sqlite3
import pandas as pd
import logging

class Olist:
    db_path = ''
    logger = logging.getLogger(__name__)

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def connect_data(self):
        self.db_path = '/Users/peter.boucher/.cache/kagglehub/datasets/terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database/versions/1/olist.sqlite'
        db_connection = sqlite3.connect(self.db_path)
        return db_connection
    
    def execute_sql_query(self, query, iteration=0):
        if not isinstance(query, str):
            self.logger.error("Query must be a string, found", query.__class__)
            raise ValueError("Query must be a string")
        elif iteration > 3:
            self.logger.error("Iteration limit exeeded: ", iteration)
            raise ValueError("Iteration limit exeeded")
        
        try:
            conn = self.connect_data()
            self.logger.info(f"Executing SQL query:\n{query}")
            result = pd.read_sql_query(query, conn)
            self.logger.info(f"Query executed successfully")
            self.logger.info(f"Result: {result}")
            return result
        except Exception as e:
            #TODO: catch sqlaclchemy.exc.ProgrammingError, sqlalchemy.exc.OperationalError
            self.logger.error(f"An error occurred: {e}")
            raise e
