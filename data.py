import logging
import sqlite3
from os import path, scandir
from sqlite3 import Error
from re import split


LOGIN, PASSWORD, GROUP_ID, IMAGE_NAME, DB_PATH, URL, PARTITION = None, None, None, None, None, None, None
INSERT_QUERY, SELECT_QUERY, UPDATE_QUERY, GET_STATS = None, None, None, None

logging.basicConfig(level=logging.INFO)

script_name = path.basename(__file__)
data_logger = logging.getLogger(name=script_name)
data_logger.setLevel(level=logging.INFO)

file_handler = logging.FileHandler(filename=f"logs/{path.splitext(script_name)[0]}.log")
formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s")
file_handler.setFormatter(fmt=formatter)

data_logger.addHandler(hdlr=file_handler)


def set_variables():
    for file in scandir("config"):
        try:
            with open(file=file.path, mode="r") as settings:
                for setting in settings.readlines():
                    variable, value = tuple(split(pattern="=", string=setting.rstrip(), maxsplit=1))
                    globals()[variable] = value
        except FileNotFoundError:
            data_logger.error(msg=f"Не найден файл {file}")


def create_connection(db_path):
    try:
        connection = sqlite3.connect(database=f"file:{db_path}?mode=rw", uri=True)
    except sqlite3.OperationalError as error:
        data_logger.error(msg=error)
    else:
        return connection


def links_to_db(db_path, query, links):
    with create_connection(db_path=db_path) as connection:
        cursor = connection.cursor()
        try:
            for link in links:
                cursor.execute(query, (link, 0))
        except Error:
            data_logger.error(msg=Error)
        else:
            connection.commit()


def get_random_link(db_path, select_query, update_query):
    connection = create_connection(db_path=db_path)
    connection.row_factory = lambda c, row: row[0]
    cursor = connection.cursor()
    random_link = None
    try:
        cursor.execute(select_query)
    except Error:
        data_logger.error(msg=Error)
    else:
        random_link = cursor.fetchone()
        if random_link:
            cursor.execute(update_query, (random_link,))
            connection.commit()
    finally:
        connection.close()
    return random_link


def get_db_stats(db_path, get_query):
    connection = create_connection(db_path=db_path)
    cursor = connection.cursor()
    stats = {}
    try:
        cursor.execute(get_query)
    except Error:
        data_logger.error(msg=Error)
    else:
        for was_used, url_number in cursor.fetchall():
            stats[was_used] = url_number
    finally:
        connection.close()
    return stats
