from os import path, remove

from requests import get
from vk_api import VkApi, VkUpload

import data


def save_image(url, db_path, select_query, update_query):
    link = data.get_random_link(db_path=db_path, select_query=select_query, update_query=update_query)
    image_path = f"{data.IMAGE_NAME}{link[-4:]}"
    with open(file=image_path, mode="wb") as file:
        file.write(get(url=f"{url}{link}").content)
    return image_path


def add_post(login, password, group_id, image_name):
    vk_session = VkApi(login, password)
    vk_session.auth()

    upload = VkUpload(vk_session)
    photo = upload.photo_wall(photos=image_name, group_id=abs(int(group_id)))

    vk = vk_session.get_api()
    vk.wall.post(owner_id=int(group_id), from_group=1, attachments=f"photo{photo[0]['owner_id']}_{photo[0]['id']}")


def delete_image(image_name):
    remove(path.join(path.abspath(path.dirname(__file__)), image_name))


data.set_variables()
image = save_image(url=data.URL, db_path=data.DB_PATH, select_query=data.SELECT_QUERY, update_query=data.UPDATE_QUERY)
add_post(login=data.LOGIN, password=data.PASSWORD, group_id=data.GROUP_ID, image_name=image)
delete_image(image_name=image)
