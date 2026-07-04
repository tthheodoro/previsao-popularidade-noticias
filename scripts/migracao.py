"""
Database Migration Script
-------------------------
Migrates data from Azure SQL Server to local SQLite.
"""

import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv

# Database is in the project root's data/ folder
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'portefolio.db')

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# For Azure SQL Server migration, install pymssql and set env vars:
# DB_SERVER, DB_NAME, DB_USER, DB_PASS
try:
    import pymssql
    SERVER = os.getenv('DB_SERVER')
    DATABASE = os.getenv('DB_NAME')
    USERNAME = os.getenv('DB_USER')
    PASSWORD = os.getenv('DB_PASS')
except ImportError:
    print("pymssql not installed. Run: pip install pymssql")
    exit(1)

print("Connecting to Azure SQL Server...")
conn_azure = pymssql.connect(server=SERVER, user=USERNAME, password=PASSWORD, database=DATABASE)

print("Creating local SQLite file...")
conn_sqlite = sqlite3.connect(DB_PATH)

tabelas = ['Utilizadores', 'Feedback', 'Feedback_Social', 'Dataset_Social_Real', 'Noticias']

for tabela in tabelas:
    print(f"Copying table: {tabela}...")
    df = pd.read_sql(f"SELECT * FROM dbo.{tabela}", conn_azure)
    df.to_sql(tabela, conn_sqlite, if_exists='replace', index=False)

conn_azure.close()
conn_sqlite.close()
print(f"Migration complete! File '{DB_PATH}' created.")
