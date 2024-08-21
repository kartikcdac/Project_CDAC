#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 12:01:20 2024

@author: kartikjindal
"""

import requests
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine

# GitHub repository details
owner = "kartikcdac"
repo = "Project_CDAC"
branch = "main"  # e.g., 'main' or 'master'
path = "Database_files/Production"  # Path within the repo

# GitHub API URL to list files in the repository
api_url = f"https://api.github.com/repos/kartikcdac/Project_CDAC/contents/Database_files/Production?ref=main"

# Make a GET request to the GitHub API
response = requests.get(api_url)
files = response.json()

# Check if response is valid
if not isinstance(files, list):
    raise ValueError("Error fetching files. Response is not a list.")

# Initialize an empty dictionary to store DataFrames
dataframes = {}

primary_keys = {
    "Production.Location": ["LocationID"], 
    "Production.ScrapReason": ["ScrapReasonID"],
    "Production.TransactionHistory": ["TransactionID"],
    "Production.TransactionHistoryArchive": ["TransactionID"],
    "Production.UnitMeasure": ["UnitMeasureCode"],
    "Production.WorkOrder": ["WorkOrderID"],
    "Production.WorkOrderRouting": ["WorkOrderID", "ProductID", "OperationSequence"],
    "Production.BillOfMaterials": ["BillOfMaterialsID"],
    "Production.Culture": ["CultureID"],
    "Production.Illustration": ["IllustrationID"],
    "Production.Product": ["ProductID"],
    "Production.ProductCategory": ["ProductCategoryID"],
    "Production.ProductCostHistory": ["ProductID", "StartDate"],
    "Production.ProductDescription": ["ProductDescriptionID"],
    "Production.ProductInventory": ["ProductID", "LocationID"],
    "Production.ProductListPriceHistory": ["ProductID", "StartDate"],
    "Production.ProductModel": ["ProductModelID"],
    "Production.ProductReview": ["ProductReviewID"],
    "Production.ProductSubcategory": ["ProductSubcategoryID"]
    }

# Loop through each file in the repository
for file in files:
    if file['name'].endswith('.csv'):
        # Get the raw URL of the CSV file
        csv_url = file['download_url']
        
        # Download the CSV file
        csv_response = requests.get(csv_url)
        
        # Check if response is valid
        if csv_response.status_code == 200:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(StringIO(csv_response.text))
            
            # Clean the DataFrame by dropping rows with missing values
            df.dropna(inplace=True)
            
            # Store the DataFrame in the dictionary with the filename as the key
            file_name = file['name'].replace('.csv', '')
            schema_name = file_name.split('.')[0]
            table_name = file_name.split('.')[1]
            
            # Check for duplicates in primary key columns and remove them
            primary_key_columns = primary_keys.get(f"{schema_name}.{table_name}", [])
            if primary_key_columns:
                df.drop_duplicates(subset=primary_key_columns, inplace=True)
            
            dataframes[table_name] = df
            print(f"Loaded and cleaned data from {file['name']} into DataFrame.")
        else:
            print(f"Failed to download {file['name']}.")

# PostgreSQL connection details
db_user = 'postgres'
db_password = 'Karjin545cdac'
db_host = 'localhost'
db_port = '5433'
db_name = 'test_ware'


# Validation function
def validate_dataframe(df, file_name):
    # Example validations (customize these as per your schema requirements)
    
    # Check data types (automatically inferred types)
    inferred_dtypes = df.dtypes
    print(f"Data types for {table_name}:\n{inferred_dtypes}")

    # Comprehensive data type expectations for validation
    expected_type_map = {
        'int64': 'int',
        'float64': 'float',
        'object': 'string',  # General string type
        'bool': 'bool',
        'datetime64[ns]': 'datetime',
        'timedelta[ns]': 'timespan',
        'category': 'categorical',
        # PostgreSQL-specific mappings
        'varchar': 'string',
        'nvarchar': 'string',
        'timestamp': 'datetime',
        'text': 'string'
    }

    for column, dtype in inferred_dtypes.items():
        expected_type = expected_type_map.get(str(dtype), None)
        if expected_type is None:
            print(f"Warning: {table_name} column {column} has an unexpected data type: {dtype}")
    
    
# Create the PostgreSQL engine
engine = create_engine(f'postgresql+psycopg2://postgres:Karjin545cdac@localhost:5433/test_ware')

# Upload each DataFrame to PostgreSQL as a table
for table_name, df in dataframes.items():
    try:
        # Write the DataFrame to PostgreSQL
        df.to_sql(table_name, engine, schema= "Production", if_exists='replace', index=False)
        print(f"DataFrame {table_name} uploaded to PostgreSQL successfully.")
    except Exception as e:
        print(f"Error uploading {table_name}: {e}")

# Optionally, you can close the engine connection after operations are done
engine.dispose()