# -*- coding: utf-8 -*-
"""
:authors: 4anky
"""

import itertools
import logging
import os
import random

import psycopg2
import requests
import vk_api
from vk_api import exceptions
from psycopg2 import errors


def create_logger():
    fmt = "%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s"

    logging.basicConfig(level=logging.INFO)

    script_name = os.path.basename(__file__)
    logger = logging.getLogger(name=script_name)
    file_handler = logging.FileHandler(filename=f"logs/{os.path.splitext(script_name)[0]}.log")
    formatter = logging.Formatter(fmt=fmt)

    file_handler.setFormatter(fmt=formatter)
    logger.setLevel(level=logging.INFO)
    logger.addHandler(hdlr=file_handler)
    return logger


class Database(object):
    """Взаимодействие с базой данных PostgreSQL."""

    def __init__(self, database=None):
        """Инициализация экземпляра класса.

        :param database: параметры подключения к базе данных
        :type database: SectionProxy
        """

        self.host = database['host']
        self.database = database['database']
        self.user = database['user']
        self.db_password = database['db_password']
        self.port = database['port']

        self.logger = logging.getLogger(__name__)

    def create_connection(self):
        """Создание соединения с базой данных.

        :return connection: объект соединения
        """

        try:
            connection = psycopg2.connect(
                host=self.host, database=self.database, user=self.user, password=self.db_password, port=self.port
            )
        except psycopg2.OperationalError as error:
            self.logger.error(msg=error)
        else:
            return connection

    def links_to_db(self, links):
        """Сохраняет уникальные URL изображений в базу данных
        и получает количество неиспользованных URL.

        :param links: коллекция URL изображений
        :type links: set

        :return: количество неиспользованных URL изображений
        :rtype: int
        """

        insert = '''INSERT INTO images_bank 
                    VALUES (%s, %s)
        '''
        select = '''SELECT COUNT(url) 
                      FROM images_bank 
                     WHERE was_used = %s
        '''
        unique_violation_code = "23505"

        with self.create_connection() as connection:
            cursor = connection.cursor()

            for link in links:
                try:
                    cursor.execute(insert, (link, False))
                except errors.lookup(code=unique_violation_code):
                    connection.rollback()
            connection.commit()

            cursor.execute(select, (False, ))
            return cursor.fetchone()[0]

    def get_random_link(self):
        """Извлекает случайный URL изображения из базы данных,
        помечает его как использованный. Получает количество
        неиспользованных URL.

        :return: кортеж из двух элементов: количество неиспользованных
        URL (int) и случайный URL (str) из базы данных
        :rtype: tuple
        """

        select_url = '''SELECT url 
                          FROM images_bank 
                         WHERE was_used = %s 
                      ORDER BY RANDOM() 
                         LIMIT 1
        '''
        update = '''UPDATE images_bank 
                       SET was_used = %s 
                     WHERE url = %s
        '''
        select_count = '''SELECT COUNT(url) 
                            FROM images_bank 
                           WHERE was_used = %s
        '''
        not_used_number = None
        random_link = None

        with self.create_connection() as connection:
            cursor = connection.cursor()

            try:
                cursor.execute(select_url, (False, ))
            except psycopg2.OperationalError:
                self.logger.error(msg=psycopg2.OperationalError)
            else:
                random_link = cursor.fetchone()[0]

            if random_link:
                cursor.execute(update, (True, random_link))
                connection.commit()
                cursor.execute(select_count, (False, ))
                not_used_number = cursor.fetchone()[0]

        return not_used_number, random_link


class Poster(Database):
    """Взаимодействие с Вконтакте API."""

    # Имя изображения при сохранении в директорию скрипта
    IMAGE_NAME = "post_image.jpg"

    def __init__(self, database, vk=None, site=None, local=None):
        """Инициализация экземпляра класса.

        :param database: параметры подключения к базе данных
        :type database: SectionProxy

        :param vk: параметры авторизации Вконтакте
        :type vk: SectionProxy

        :param site: параметры сайта, с которого сохраняются URL изображений
        (на данный момент https://2ch.hk)
        :type site: SectionProxy

        :param local: единственный параметр: путь до файла с хештегами
        :type local: SectionProxy
        """

        super().__init__(database)

        self.ht_file = local['ht_file']
        self.url = site['url']

        self.login = vk['login']
        self.vk_password = vk['vk_password']
        self.group_id = vk['group_id']

        self.logger = logging.getLogger(__name__)

    def hash_tags_from_file(self):
        """Извлекает случайное количество различных хештегов из файла с хештегами.

        :return: строка с хештегами
        :rtype: str
        """

        first_hash_tag = "#synceyes"
        hash_tags_number = random.randint(9, 15)

        with open(file=self.ht_file, mode="r") as file:
            all_hash_tags = file.read().split("\n")

        hash_tags = list(random.choices(population=all_hash_tags, k=hash_tags_number))
        hash_tags.insert(0, first_hash_tag)
        return " ".join(hash_tags)

    def save_image(self):
        """Сохраняет изображение в директории скрипта.

        :return: кортеж из двух элементов: число неиспользованных
        URL изображений (int) и индикатор сохранения изображения
        в директории скрипта (bool)
        :rtype: tuple
        """

        not_used_number, link = self.get_random_link()

        with open(file=self.IMAGE_NAME, mode="wb") as file:
            file.write(requests.get(url=f"{self.url}{link}").content)

        if os.path.exists(path=self.IMAGE_NAME):
            is_saved = True
            self.logger.info(msg="Изображение сохранилось на сервере скрипта")
        else:
            is_saved = False
            self.logger.error(msg="Не удалось сохранить изображение")

        return not_used_number, is_saved

    def add_post(self):
        """Проходит аутентификацию Вконтакте, загружает изображение
        из директории скрипта на сервер соц. сети и публикует пост
        в сообществе с хештегами и данным изображением.
        """

        vk_session = None

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
            vk.wall.post(
                owner_id=int(self.group_id),
                from_group=1,
                message=self.hash_tags_from_file(),
                attachments=f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
            )
            self.logger.info(msg="Пост с изображением опубликован")

    def delete_image(self):
        """Удаляет изображение из директории скрипта."""

        try:
            os.remove(os.path.join(os.path.abspath(os.path.dirname(__file__)), self.IMAGE_NAME))
        except exceptions:
            self.logger.error(msg="Не удалось удалить изображение с сервера скрипта")
        else:
            self.logger.info(msg="Изображение успешно удалено с сервера скрипта")


class Parser(object):
    """Взаимодествие с сайтом, с которого сохраняются URL изображений."""

    def __init__(self, site=None):
        """Инициализация экземпляра класса.

        :param site: параметры сайта, с которого сохраняются URL изображений
        (на данный момент https://2ch.hk)
        :type site: SectionProxy
        """

        self.url = site['url']
        self.section = site['section']

        self.logger = logging.getLogger(__name__)

    @staticmethod
    def check_vk_requirements(media_file):
        """Проверяет параметры изображения на соответствие требованиям
        Вконтакте и сообщества. Используется во время парсинга URL изображений.

        :param media_file: структура, содержащая параметры изображения
        :type media_file: dict

        :return: индикатор соответствия требованиям
        :rtype: bool
        """

        if media_file['type'] in {1, 2}:
            if 400 <= media_file['width'] <= 5000:
                if 350 <= media_file['height'] <= 5000:
                    return True
        return False

    def get_images(self):
        """В указанной секции сайта ищет URL всех изображений.
        Указание секции для поиска производится в конфигурационном файле.

        :return: набор уникальных URL изображений
        :rtype: set
        """

        threads_no = set()
        links = set()

        # Получаем номера всех тредов в указанной секции 2ch.hk
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
        for thread in threads_no:
            thread = requests.get(url=f"{self.url}/{self.section}/res/{thread}.json").json()
            posts = thread['threads'][0]['posts']
            for post in posts:
                for media in post['files']:
                    if self.check_vk_requirements(media_file=media):
                        links.add(media['path'])
        return links
