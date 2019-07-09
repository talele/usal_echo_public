from json import load
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema
from sqlalchemy import inspect
import pandas as pd
import os


def _load_json_credentials(filepath):
    """Load json formatted credentials.
    
    :params filepath (str): path to credentials file
    "returns: credentials as dict
    
    """
    with open(filepath) as f:
        credentials = load(f)

    return credentials


class dbReadWriteData:   
    """
    Class for reading and writing data to and from postgres database.
    
    **Requirements
        credentials file formatted as:
            {
            "user":"your_user",
            "host": "your_server.rds.amazonaws.com",
            "database": "your_database",
            "psswd": "your_password"
            }
            
    :param credentials_file (str): path to credentials file, default="~/.psql_credentials.json"
    :param schema (str): database schema 
            
    """    
    def __init__(self, schema=None, credentials_file="~/.psql_credentials.json"):
        self.filepath = os.path.expanduser(credentials_file)
        self.schema = schema
        self.credentials = _load_json_credentials(self.filepath)
        self.connection_str =  "postgresql://{}:{}@{}/{}".format(self.credentials['user'],
                                                             self.credentials['psswd'],
                                                             self.credentials['host'],
                                                             self.credentials['database'])
        self.engine = create_engine(self.connection_str, encoding='utf-8')
        

    def save_to_db(self, df, db_table, if_exists='replace'):
        """Write dataframe to table in database.
        
        :param df (pandas.DataFrame): dataframe to save to database
        :param db_table (str): name of database table to write to
        
        """
        df.to_sql(db_table, self.engine, self.schema, if_exists, index=False)
        
    
    def get_table(self, db_table):
        """Read table in database as dataframe.
        
        :param db_table (str): name of database table to read
        """
          
        df = pd.read_sql_table(db_table, self.engine, self.schema)
        
        return df
    
    
    def list_tables(self):
        """List tables in database.
        
        """
        inspector = inspect(self.engine)
        print(inspector.get_table_names(self.schema))
       
        
    
class dbReadWriteRaw(dbReadWriteData):
    """
    
    """    
    def __init__(self):
        super().__init__(schema='raw')
        if not self.engine.dialect.has_schema(self.engine, self.schema):
            self.engine.execute(CreateSchema(self.schema))

            
            
class dbReadWriteClean(dbReadWriteData):
    """
    
    """    
    def __init__(self):
        super().__init__(schema='clean')
        if not self.engine.dialect.has_schema(self.engine, self.schema):
            self.engine.execute(CreateSchema(self.schema))