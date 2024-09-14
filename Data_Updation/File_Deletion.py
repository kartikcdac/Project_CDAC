#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 17:46:44 2024

@author: kartikjindal
"""

import os
import requests

# GitHub repository details
owner = "kartikcdac"
repo = "Project_CDAC"
branch = "main"
path = "Project_CDAC/Data_Loading/Data_Append"
github_token = os.getenv("github_token")

# Function to delete files from GitHub after data is loaded
def delete_files_from_github():
    api_url = f"https://api.github.com/repos/kartikcdac/Project_CDAC/contents/Data_Loading/Data_Append?ref=main"
    headers = {'Authorization': f'Bearer {github_token}'}
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 403:
        raise ValueError("GitHub API rate limit exceeded.")
    elif response.status_code != 200:
        raise ValueError(f"Error fetching files for deletion. Status code: {response.status_code}")
    
    files = response.json()
    
    if not isinstance(files, list):
        raise ValueError("Error fetching files. Response is not a list.")
    
    for file in files:
        if file['name'].endswith('.csv'):
            delete_url = f"https://api.github.com/repos/kartikcdac/Project_CDAC/contents/Data_Loading/Data_Append/{file['name']}"
            delete_response = requests.delete(delete_url, headers=headers, json={
                "message": f"Delete {file['name']} after loading to PostgreSQL",
                "sha": file['sha']
            })
            if delete_response.status_code == 200:
                print(f"File {file['name']} deleted successfully.")
            else:
                print(f"Error deleting file {file['name']}: {delete_response.status_code}")

if __name__ == "__main__":
    delete_files_from_github()
