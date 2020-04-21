from os import path, remove
from random import choice
from requests import get

from bs4 import BeautifulSoup
from vk_api import VkApi, VkUpload


def save_random_image(url, tag, attr, image_name):
    html = get(url=url).text
    all_image_links = BeautifulSoup(html, "html.parser").find_all(tag, attrs={attr: True})
    collection = [f"{url[:-4]}{image_link[attr]}" for image_link in all_image_links if "/sn/" in image_link[attr]]

    image = get(choice(seq=collection)).content
    with open(file=image_name, mode="wb") as file:
        file.write(image)


def add_post(login, password, group_id, image_name):
    vk_session = VkApi(login, password)
    vk_session.auth(token_only=True)

    upload = VkUpload(vk_session)
    photo = upload.photo_wall(photos=image_name, group_id=abs(int(group_id)))

    vk = vk_session.get_api()
    vk.wall.post(owner_id=int(group_id), from_group=1, attachments=f"photo{photo[0]['owner_id']}_{photo[0]['id']}")


def delete_image(image_name):
    remove(path.join(path.abspath(path.dirname(__file__)), image_name))


LOGIN, PASSWORD, GROUP_ID, IMAGE_NAME, URL, TAG, ATTRIBUTE = None, None, None, None, None, None, None
with open(file="local_settings", mode="r") as settings:
    for param in settings.readlines():
        variable, value = tuple(param.rstrip().split("="))
        globals()[variable] = value

save_random_image(url=URL, tag=TAG, attr=ATTRIBUTE, image_name=IMAGE_NAME)
add_post(login=LOGIN, password=PASSWORD, group_id=GROUP_ID, image_name=IMAGE_NAME)
delete_image(image_name=IMAGE_NAME)
