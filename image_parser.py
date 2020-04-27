from itertools import count

from requests import get

import data


def check_vk_requirements(data_file):
    if data_file['type'] in {1, 2}:
        if 400 <= data_file['width'] <= 5000:
            if 350 <= data_file['height'] <= 5000:
                return True
    return False


def get_images_from_2ch_section(url, section):
    links = set()
    for page in count(start=1, step=1):
        response = get(url=f"{url}/{section}/{page}.json")
        if response.status_code == 200:
            threads = response.json()['threads']
            for thread in threads:
                for post in thread['posts']:
                    for file in post['files']:
                        if check_vk_requirements(data_file=file):
                            links.add(file['path'])
        else:
            break
    return links


data.set_variables()
image_links = get_images_from_2ch_section(url=data.URL, section=data.PARTITION)
data.links_to_db(db_path=data.DB_PATH, query=data.INSERT_QUERY, links=image_links)
