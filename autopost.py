import logging
from os import path, remove

from requests import get
from vk_api import VkApi, VkUpload, exceptions

import data


script_name = path.basename(__file__)
post_logger = logging.getLogger(name=script_name)
post_logger.setLevel(level=logging.INFO)

file_handler = logging.FileHandler(filename=f"logs/{path.splitext(script_name)[0]}.log")
formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s")
file_handler.setFormatter(fmt=formatter)

post_logger.addHandler(hdlr=file_handler)


def save_image(url, db_path, select_query, update_query):
    link = data.get_random_link(db_path=db_path, select_query=select_query, update_query=update_query)
    image_path = f"{data.IMAGE_NAME}{link[-4:]}"
    with open(file=image_path, mode="wb") as file:
        file.write(get(url=f"{url}{link}").content)
    if path.exists(path=image_path):
        post_logger.info(msg="Изображение сохранилось на сервере скрипта")
    else:
        post_logger.error(msg="Не удалось сохранить изображение")
    return image_path


def add_post(login, password, group_id, image_name):
    vk_session, photo = None, None
    try:
        vk_session = VkApi(login, password)
        vk_session.auth()
    except exceptions.AuthError:
        post_logger.error(msg="Не удалось пройти аутентификацию VK")

    upload = VkUpload(vk_session)
    vk = vk_session.get_api()
    try:
        photo = upload.photo_wall(photos=image_name, group_id=abs(int(group_id)))
    except exceptions:
        post_logger.error(msg="Не удалось загрузить фотографию на сервер VK")
    else:
        vk.wall.post(owner_id=int(group_id), from_group=1, attachments=f"photo{photo[0]['owner_id']}_{photo[0]['id']}")
        post_logger.info(msg="Пост с изображением опубликован")


def delete_image(image_name):
    try:
        remove(path.join(path.abspath(path.dirname(__file__)), image_name))
    except exceptions:
        post_logger.error(msg="Не удалось удалить изображение с сервера скрипта")
    else:
        post_logger.info(msg="Изображение успешно удалено с сервера скрипта")


data.set_variables()
image = save_image(url=data.URL, db_path=data.DB_PATH, select_query=data.SELECT_QUERY, update_query=data.UPDATE_QUERY)
add_post(login=data.LOGIN, password=data.PASSWORD, group_id=data.GROUP_ID, image_name=image)
delete_image(image_name=image)
