import logging
from os import path, remove
from random import choices, randint

from requests import get
from vk_api import VkApi, VkUpload, exceptions

import data


logging.basicConfig(level=logging.INFO)

script_name = path.basename(__file__)
post_logger = logging.getLogger(name=script_name)
post_logger.setLevel(level=logging.INFO)

file_handler = logging.FileHandler(filename=f"logs/{path.splitext(script_name)[0]}.log")
formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s")
file_handler.setFormatter(fmt=formatter)

post_logger.addHandler(hdlr=file_handler)


def hash_tags_from_file(file):
    with open(file=file, mode="r") as ht_file:
        all_hash_tags = ht_file.read().split("\n")
    ht_number = randint(9, 15)
    res = list(choices(population=all_hash_tags, k=ht_number))
    res.insert(0, "#synceyes")
    return " ".join(res)


def save_image(url):
    not_used_number, link = data.get_random_link()
    image_path = f"{data.IMAGE_NAME}{link[-4:]}"
    with open(file=image_path, mode="wb") as file:
        file.write(get(url=f"{url}{link}").content)
    if path.exists(path=image_path):
        post_logger.info(msg="Изображение сохранилось на сервере скрипта")
    else:
        post_logger.error(msg="Не удалось сохранить изображение")
    return not_used_number, image_path


def add_post(login, password, group_id, image_name, message):
    vk_session, photo = None, None
    try:
        vk_file_handler = logging.FileHandler(filename=f"logs/{path.splitext(script_name)[0]}.log")
        vk_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s"
        )
        vk_file_handler.setFormatter(fmt=vk_formatter)

        vk_session = VkApi(login, password)
        vk_session.logger.addHandler(hdlr=vk_file_handler)
        vk_session.auth()
    except exceptions.AuthError:
        post_logger.error(msg="Не удалось пройти аутентификацию VK")

    upload = VkUpload(vk_session)
    vk = vk_session.get_api()
    try:
        photo = upload.photo_wall(photos=image_name, group_id=abs(int(group_id)))
    except exceptions.ApiError:
        post_logger.exception(msg="Не удалось загрузить фотографию на сервер VK")
    else:
        vk.wall.post(owner_id=int(group_id),
                     from_group=1,
                     message=message,
                     attachments=f"photo{photo[0]['owner_id']}_{photo[0]['id']}")
        post_logger.info(msg="Пост с изображением опубликован")


def delete_image(image_name):
    try:
        remove(path.join(path.abspath(path.dirname(__file__)), image_name))
    except exceptions:
        post_logger.error(msg="Не удалось удалить изображение с сервера скрипта")
    else:
        post_logger.info(msg="Изображение успешно удалено с сервера скрипта")
