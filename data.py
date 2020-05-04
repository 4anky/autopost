import logging
import sqlite3
from os import path, scandir
from sqlite3 import Error
from re import split


LOGIN, PASSWORD, GROUP_ID, IMAGE_NAME, DB_PATH, HT_FILE, URL, PARTITION = None, None, None, None, None, None, None, None

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


def links_to_db(db_path, links):
    with create_connection(db_path=db_path) as connection:
        connection.row_factory = lambda c, row: row[0]
        cursor = connection.cursor()
        try:
            for link in links:
                cursor.execute("INSERT OR IGNORE INTO images_bank(url, was_used) VALUES (?, ?)", (link, 0))
        except Error:
            data_logger.error(msg=Error)
        else:
            connection.commit()
            cursor.execute("SELECT COUNT(url) FROM images_bank WHERE was_used = 0")
            return cursor.fetchone()


def get_random_link(db_path):
    not_used_number, random_link = None, None
    with create_connection(db_path=db_path) as connection:
        connection.row_factory = lambda c, row: row[0]
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT * "
                           "FROM (SELECT url FROM images_bank WHERE was_used = 0 ORDER BY RANDOM() LIMIT 1) "
                           "UNION "
                           "SELECT * "
                           "FROM (SELECT COUNT(url) FROM images_bank WHERE was_used = 0)")
        except Error:
            data_logger.error(msg=Error)
        else:
            not_used_number, random_link = tuple(cursor.fetchall())
            if random_link:
                cursor.execute("UPDATE images_bank SET was_used = 1 WHERE url = ?", (random_link,))
                connection.commit()
    return not_used_number, random_link
