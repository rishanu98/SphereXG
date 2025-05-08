import click, requests, json
import sqlite3
from utils.valid import get_token, sqlite_save, download_file
from concurrent.futures import ThreadPoolExecutor
from utils.commands import initialize_project, fetch, download
    
@click.group()
def cli():
    """CLI tools for HoloBuilder Project Management"""
    pass

cli.add_command(initialize_project)
cli.add_command(fetch)
cli.add_command(download)

if __name__ == '__main__':
    cli()


