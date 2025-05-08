import click
import requests
import sqlite3
import json
from concurrent.futures import ThreadPoolExecutor
from utils.valid import get_token, sqlite_save, download_file


@click.command(name='initialize')
@click.argument("project_id")
def initialize_project(project_id):

    token = get_token(project_id)

    click.echo(f"✅ Token retrieved successfully")
    # Here you can add the logic to initialize the project using the token
    data = requests.post(
        url= f"https://v2.project.api.dev.holobuilder.eu/v1/{project_id}/ielements",
        headers={"Authorization": f"Bearer {token}"},
    )

    if data.status_code == 200:
        data = data.json()
        click.echo(f"Project {project_id} initialized successfully.")
        # Save the project data to a SQLite database
        sqlite_save(data)
        click.echo(f"Project data saved to SQLite database.")
    else:
        click.echo(f"Failed to initialize project: {data.status_code} - {data.text}")

@click.command(name='query')  # -1 means it can take any number of arguments
@click.argument("query", type=str,nargs=-1)  # Accepts any number of arguments
@click.option('-j','--json_result', type=str, default='query_result.json', help='Enter the path to save the query result')
def fetch(query, json_result):
    """Execute a SQL query on the SQLite database"""
    query = " ".join(query)  # Join the arguments into a single string
    print(query)
    conn = sqlite3.connect("project_cache.db")
    conn.row_factory = sqlite3.Row  # SQLite to return each row from a query as a sqlite3.Row object instead of the default tuple.
    cursor = conn.cursor()
    #row = cursor.fetchone()
    #names = row.keys()
    #column_names= [desc[0] for desc in cursor.description]
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    if results:
        results = [dict(row) for row in results]  # Convert rows to dictionaries
        with open(json_result, "w") as f:
            f.truncate()  # Clear the file before writing
            json.dump(results, f, indent=4)
        click.echo(f"✅ Query executed successfully. {len(results)} Results saved to {json_result}.")
    else:
        click.echo(f"No results found for query: {query}")

@click.command(name='download-all')    # Register this function as a subcommand of this specific cli group.
@click.option('-f','--folder', type=str, default='download',help='Enter the folder path to save the files')
@click.option('-t','--type', type=str, default=None, help='Enter the type of files to download')
def download(folder,type):
    """Download all URIs into the given folder"""

    conn = sqlite3.connect(f"project_cache.db")
    cursor = conn.cursor()
    if type:
        uris = cursor.execute("SELECT uri FROM iElements WHERE uri IS NOT NULL AND type = ?", (type,))
        folder = f"./{folder}/{type}"
    else:
        uris = cursor.execute("SELECT uri FROM iElements WHERE uri IS NOT NULL").fetchall() # uri is list of tuples
    urls = [url[0] for url in uris if url[0] is not None] # converting list of tuples to list of strings

    try:   
        with ThreadPoolExecutor(max_workers=8) as executor:
            for i, url in enumerate(urls):
                executor.submit(download_file, url, i + 1, len(urls), folder)
    except Exception as e:
        print(f"Error downloading : {e}")
    
    conn.close()
    click.echo(f"✅ Downloaded {len(urls)} files successfully.")