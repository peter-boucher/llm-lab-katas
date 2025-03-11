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
    
    def execute_sql_query(self, query, prompt='', iteration=0):
        if not isinstance(query, str):
            self.logger.error("Query must be a string, found", query.instance())
            raise ValueError("Query must be a string")
        try:
            conn = self.connect_data()
            self.logger.info(f"Executing SQL query:\n{query}")
            result = pd.read_sql_query(query, conn)
            return result
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            if iteration > 3:
                improved_sql = generate_fix(e, query, prompt)
                extracted_sql = extract_sql(improved_sql['choices'][0]['message']['content'])
                return self.execute_sql_query(extracted_sql, iteration+1)
            else:
                self.logger.error(f"Maximum fix attempts reached")
                raise e
