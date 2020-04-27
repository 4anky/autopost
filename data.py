import sqlite3
from os import scandir
from sqlite3 import Error
from re import split


LOGIN, PASSWORD, GROUP_ID, IMAGE_NAME, DB_PATH, URL, PARTITION = None, None, None, None, None, None, None
INSERT_QUERY, SELECT_QUERY, UPDATE_QUERY = None, None, None


def set_variables():
    for file in scandir("config"):
        with open(file=file.path, mode="r") as settings:
            for setting in settings.readlines():
                variable, value = tuple(split(pattern="=", string=setting.rstrip(), maxsplit=1))
                globals()[variable] = value


def create_connection(db_path):
    try:
        connection = sqlite3.connect(database=db_path)
    except Error:
        print(Error)
    else:
        return connection


def links_to_db(db_path, query, links):
    connection = create_connection(db_path=db_path)
    cursor = connection.cursor()
    for link in links:
        cursor.execute(query, (link, 0))
    connection.commit()
    connection.close()


def get_random_link(db_path, select_query, update_query):
    connection = create_connection(db_path=db_path)
    connection.row_factory = lambda c, row: row[0]
    cursor = connection.cursor()
    random_link = None
    try:
        cursor.execute(select_query)
    except Error:
        print(Error)
    else:
        random_link = cursor.fetchone()
        if random_link:
            cursor.execute(update_query, (random_link,))
            connection.commit()
    finally:
        connection.close()
    return random_link
