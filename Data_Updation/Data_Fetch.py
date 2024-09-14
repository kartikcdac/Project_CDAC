#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 17:43:00 2024

@author: kartikjindal
"""

import requests
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine, text
import os

# GitHub repository details
owner = "kartikcdac"
repo = "Project_CDAC"
branch = "main"
path = "Project_CDAC/Data_Loading/Data_Append"
github_token = os.getenv("github_token")

# PostgreSQL connection details
POSTGRES_URI = 'postgresql://postgres:Karjin545cdac2@172.16.86.130:5432/datawarehouse_aw'

# Define primary keys for each table
primary_keys = {
    "Sales.SalesOrderDetail": ["SalesOrderID", "SalesOrderDetailID"],
    "Sales.SalesOrderHeader": ["SalesOrderID"],
    "Sales.SalesOrderHeaderSalesReason": ["SalesOrderID", "SalesReasonID"],
    "Sales.SalesPersonQuotaHistory": ["BusinessEntityID", "QuotaDate"],
    "Sales.SalesReason": ["SalesReasonID"],
    "Sales.SalesTaxRate": ["SalesTaxRateID"],
    "Sales.SalesTerritory": ["TerritoryID"],
    "Sales.ShoppingCartItem": ["ShoppingCartItemID"],
    "Sales.SpecialOffer": ["SpecialOfferID"],
    "Sales.SpecialOfferProduct": ["SpecialOfferID", "ProductID"],
    "Sales.Store": ["BusinessEntityID"],
    "Sales.CountryRegionCurrency": ["CountryRegionCode", "CurrencyCode"],
    "Sales.CreditCard": ["CreditCardID"],
    "Sales.Currency": ["CurrencyCode"],
    "Sales.CurrencyRate": ["CurrencyRateID"],
    "Sales.Customer": ["CustomerID"],
    "Sales.PersonCreditCard": ["BusinessEntityID", "CreditCardID"],
    "Sales.SalesPerson": ["BusinessEntityID"],
    "Sales.SalesTerritoryHistory": ["BusinessEntityID", "StartDate", "TerritoryID"],
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
    "Production.ProductSubCategory": ["ProductSubcategoryID"],
    "HumanResources.Shift": ["ShiftID"],
    "HumanResources.Department": ["DepartmentID"],
    "HumanResources.Employee": ["BusinessEntityID"],
    "HumanResources.EmployeeDepartmentHistory": ["BusinessEntityID", "StartDate", "DepartmentID", "ShiftID"],
    "HumanResources.EmployeePayHistory": ["BusinessEntityID", "RateChangeDate"],
    "HumanResources.JobCandidate": ["JobCandidateID"],
    "Purchasing.ProductVendor": ["ProductID", "BusinessEntityID"],
    "Purchasing.PurchaseOrderDetail": ["PurchaseOrderID", "PurchaseOrderDetailID"],
    "Purchasing.PurchaseOrderHeader": ["PurchaseOrderID"],
    "Purchasing.ShipMethod": ["ShipMethodID"],
    "Purchasing.Vendor": ["BusinessEntityID"],
    "Person.StateProvince": ["StateProvinceID"],
    "Person.Address": ["AddressID"],
    "Person.AddressType": ["AddressTypeID"],
    "Person.BusinessEntity": ["BusinessEntityID"],
    "Person.BusinessEntityAddress": ["BusinessEntityID", "AddressID", "AddressTypeID"],
    "Person.BusinessEntityContact": ["BusinessEntityID", "PersonID", "ContactTypeID"],
    "Person.ContactType": ["ContactTypeID"],
    "Person.CountryRegion": ["CountryRegionCode"],
    "Person.EmailAddress": ["BusinessEntityID", "EmailAddressID"],
    "Person.Password": ["BusinessEntityID"],
    "Person.Person": ["BusinessEntityID"],
    "Person.PersonPhone": ["BusinessEntityID", "PhoneNumber", "PhoneNumberTypeID"],
    "Person.PhoneNumberType": ["PhoneNumberTypeID"]
    }

# Function to fetch CSV files directly from GitHub
def fetch_and_clean_data():
    api_url = f"https://api.github.com/repos/kartikcdac/Project_CDAC/contents/Data_Loading/Data_Append?ref=main"
    headers = {'Authorization': f'Bearer {github_token}'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 403:
        raise ValueError("GitHub API rate limit exceeded.")
    elif response.status_code != 200:
        raise ValueError(f"Error fetching files. Status code: {response.status_code}")

    files = response.json()
    
    if not isinstance(files, list):
        raise ValueError("Error fetching files. Response is not a list.")
    
    dataframes = {}
    for file in files:
        if file['name'].endswith('.csv'):
            csv_url = file['download_url']
            csv_response = requests.get(csv_url)

            if csv_response.status_code == 200:
                df = pd.read_csv(StringIO(csv_response.text))

                # Extract schema and table names from the file name
                file_name = file['name'].replace('.csv', '')
                schema, table_name = file_name.split('.')

                # Handle primary key constraints
                key = f"{schema}.{table_name}"
                if key in primary_keys:
                    pkeys = primary_keys[key]
                    df.dropna(subset=pkeys, inplace=True)
                    df.drop_duplicates(subset=pkeys, inplace=True)

                df.dropna(how='all', inplace=True)
                dataframes[f"{schema}.{table_name}"] = df
            else:
                raise ValueError(f"Error fetching CSV file: {file['name']}, Status code: {csv_response.status_code}")
    
    return dataframes

# Function to check if records exist in the PostgreSQL table
def check_existing_records(conn, schema, table_name, df, primary_key_columns):
    primary_key_query = " AND ".join([f'"{col}" = :{col}' for col in primary_key_columns])
    
    new_rows = []
    
    for _, row in df.iterrows():
        query = f'SELECT 1 FROM "{schema}"."{table_name}" WHERE {primary_key_query}'
        params = {col: row[col] for col in primary_key_columns}
        
        result = conn.execute(text(query), params).fetchone()
        if result is None:
            new_rows.append(row)

    return pd.DataFrame(new_rows)

# Function to upload data to PostgreSQL with deduplication logic
def upload_data_to_postgresql(dataframes):
    engine = create_engine(POSTGRES_URI)
    
    if dataframes:
        for full_table_name, df in dataframes.items():
            schema, table_name = full_table_name.split('.')
            try:
                with engine.connect() as conn:
                    # Check if table exists with case-sensitive names
                    table_exists_query = f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = :schema
                        AND table_name = :table_name
                    )
                    """
                    result = conn.execute(text(table_exists_query), {"schema": schema, "table_name": table_name}).fetchone()
                    
                    if not result[0]:
                        print(f"Table {schema}.{table_name} does not exist.")
                        continue
                    
                    key = f"{schema}.{table_name}"
                    if key in primary_keys:
                        pkeys = primary_keys[key]
                        df_new = check_existing_records(conn, schema, table_name, df, pkeys)
                        
                        if not df_new.empty:
                            df_new.to_sql(
                                table_name,
                                conn,
                                schema=schema,
                                if_exists='append',
                                index=False,
                                method='multi'
                            )
                            print(f"Uploaded {len(df_new)} new rows to {schema}.{table_name} successfully.")
                        else:
                            print(f"No new data to upload for {schema}.{table_name}.")
            except Exception as e:
                print(f"Error uploading {schema}.{table_name}: {e}")
    
    engine.dispose()

def main():
    # Fetch and clean data
    print("Fetching and cleaning data...")
    dataframes = fetch_and_clean_data()
    
    # Upload data to PostgreSQL
    print("Uploading data to PostgreSQL...")
    upload_data_to_postgresql(dataframes)

if __name__ == "__main__":
    main()
