import logging
from os import path, scandir
from psycopg2 import Error
from re import split
import psycopg2

LOGIN, PASSWORD, GROUP_ID = None, None, None
IMAGE_NAME, DB_PATH, HT_FILE = None, None, None
URL, PARTITION = None, None
PG_HOST, PG_DATABASE, PG_USER, PG_PASSWORD, PG_PORT = None, None, None, None, None

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


def create_connection():
    try:
        connection = psycopg2.connect(
            host=PG_HOST,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
            port=PG_PORT
        )
    except psycopg2.OperationalError as error:
        data_logger.error(msg=error)
    else:
        return connection


def links_to_db(links):
    with create_connection() as connection:
        connection.row_factory = lambda c, row: row[0]
        cursor = connection.cursor()
        try:
            for link in links:
                cursor.execute("INSERT OR IGNORE INTO images_bank(url, was_used) VALUES ($1, $2)", (link, False))
        except Error:
            data_logger.error(msg=Error)
        else:
            connection.commit()
            cursor.execute("SELECT COUNT(url) FROM images_bank WHERE was_used = False")
            return cursor.fetchone()


def get_random_link():
    not_used_number, random_link = None, None
    with create_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT url FROM images_bank WHERE was_used = False ORDER BY RANDOM() LIMIT 1")
        except Error:
            data_logger.error(msg=Error)
        else:
            random_link = cursor.fetchone()[0]
            if random_link:
                cursor.execute("UPDATE images_bank SET was_used = %s WHERE url = %s", (True, random_link))
                connection.commit()
                cursor.execute("SELECT COUNT(url) FROM images_bank WHERE was_used = False")
                not_used_number = cursor.fetchone()[0]
    return not_used_number, random_link.strip()
