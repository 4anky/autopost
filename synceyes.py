import itertools
import logging
import os
import random

import psycopg2
import requests
import vk_api
from vk_api import exceptions
from psycopg2 import Error


def create_logger():
    logging.basicConfig(level=logging.INFO)

    script_name = os.path.basename(__file__)
    logger = logging.getLogger(name=script_name)
    file_handler = logging.FileHandler(filename=f"logs/{os.path.splitext(script_name)[0]}.log")
    formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s")

    file_handler.setFormatter(fmt=formatter)
    logger.setLevel(level=logging.INFO)
    logger.addHandler(hdlr=file_handler)
    return logger


class Database(object):
    def __init__(self, database=None):
        self.host = database['host']
        self.database = database['database']
        self.user = database['user']
        self.db_password = database['db_password']
        self.port = database['port']

        self.logger = logging.getLogger(__name__)

    def create_connection(self):
        try:
            connection = psycopg2.connect(
                host=self.host, database=self.database, user=self.user, password=self.db_password, port=self.port
            )
        except psycopg2.OperationalError as error:
            self.logger.error(msg=error)
        else:
            return connection

    def links_to_db(self, links):
        with self.create_connection() as connection:
            connection.row_factory = lambda c, row: row[0]
            cursor = connection.cursor()
            try:
                for link in links:
                    cursor.execute("INSERT OR IGNORE INTO images_bank(url, was_used) VALUES ($1, $2)", (link, False))
            except Error:
                self.logger.error(msg=Error)
            else:
                connection.commit()
                cursor.execute("SELECT COUNT(url) FROM images_bank WHERE was_used = False")
                return cursor.fetchone()

    def get_random_link(self):
        not_used_number, random_link = None, None
        with self.create_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT url FROM images_bank WHERE was_used = False ORDER BY RANDOM() LIMIT 1")
            except Error:
                self.logger.error(msg=Error)
            else:
                random_link = cursor.fetchone()[0]
                if random_link:
                    cursor.execute("UPDATE images_bank SET was_used = %s WHERE url = %s", (True, random_link))
                    connection.commit()
                    cursor.execute("SELECT COUNT(url) FROM images_bank WHERE was_used = False")
                    not_used_number = cursor.fetchone()[0]
        return not_used_number, random_link.strip()


class Poster(Database):
    IMAGE_NAME = "post_image.jpg"

    def __init__(self, database, vk=None, site=None, local=None):
        super().__init__(database)

        self.ht_file = local['ht_file']
        self.url = site['url']

        self.login = vk['login']
        self.vk_password = vk['vk_password']
        self.group_id = vk['group_id']

        self.logger = logging.getLogger(__name__)

    def hash_tags_from_file(self):
        with open(file=self.ht_file, mode="r") as file:
            all_hash_tags = file.read().split("\n")
        ht_number = random.randint(9, 15)
        res = list(random.choices(population=all_hash_tags, k=ht_number))
        res.insert(0, "#synceyes")
        return " ".join(res)

    def save_image(self):
        not_used_number, link = self.get_random_link()
        with open(file=self.IMAGE_NAME, mode="wb") as file:
            file.write(requests.get(url=f"{self.url}{link}").content)

        if os.path.exists(path=self.IMAGE_NAME):
            self.logger.info(msg="Изображение сохранилось на сервере скрипта")
        else:
            self.logger.error(msg="Не удалось сохранить изображение")
        return not_used_number, self.IMAGE_NAME

    def add_post(self):
        vk_session, photo = None, None
        try:
            vk_session = vk_api.VkApi(self.login, self.vk_password)
            vk_session.auth()
        except exceptions.AuthError:
            self.logger.error(msg="Не удалось пройти аутентификацию VK")

        upload = vk_api.VkUpload(vk_session)
        vk = vk_session.get_api()
        try:
            photo = upload.photo_wall(photos=self.IMAGE_NAME, group_id=abs(int(self.group_id)))
        except exceptions.ApiError:
            self.logger.exception(msg="Не удалось загрузить фотографию на сервер VK")
        else:
            vk.wall.post(owner_id=int(self.group_id),
                         from_group=1,
                         message=self.hash_tags_from_file(),
                         attachments=f"photo{photo[0]['owner_id']}_{photo[0]['id']}")
            self.logger.info(msg="Пост с изображением опубликован")

    def delete_image(self):
        try:
            os.remove(os.path.join(os.path.abspath(os.path.dirname(__file__)), self.IMAGE_NAME))
        except exceptions:
            self.logger.error(msg="Не удалось удалить изображение с сервера скрипта")
        else:
            self.logger.info(msg="Изображение успешно удалено с сервера скрипта")


class Parser(object):
    def __init__(self, site=None):
        self.url = site['url'],
        self.section = site['section']

        self.logger = logging.getLogger(__name__)

    @staticmethod
    def check_vk_requirements(media_file):
        if media_file['type'] in {1, 2}:
            if 400 <= media_file['width'] <= 5000:
                if 350 <= media_file['height'] <= 5000:
                    return True
        return False

    def get_images(self):
        # Получаем номера всех тредов в указанной секции 2ch.hk
        threads_no = set()
        for page in itertools.count(start=1, step=1):
            response = requests.get(url=f"{self.url}/{self.section}/{page}.json")
            if response.status_code == 200:
                threads = response.json()['threads']
                for thread in threads:
                    threads_no.add(thread['thread_num'])
            else:
                if page == 1:
                    self.logger.error(msg=f"Парсер не посетил ни одной страницы (status_code: {response.status_code})")
                break

        # Получаем url всех картинок из каждого треда
        links = set()
        for thread in threads_no:
            thread = requests.get(url=f"{self.url}/{self.section}/res/{thread}.json").json()
            posts = thread['threads'][0]['posts']
            for post in posts:
                for media in post['files']:
                    if self.check_vk_requirements(media_file=media):
                        links.add(media['path'])
        return links
