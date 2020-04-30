from itertools import count
import logging
from os import path

from requests import get

import data


logging.basicConfig(level=logging.INFO)

script_name = path.basename(__file__)
parse_logger = logging.getLogger(name=script_name)
parse_logger.setLevel(level=logging.INFO)

file_handler = logging.FileHandler(filename=f"logs/{path.splitext(script_name)[0]}.log")
formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s")
file_handler.setFormatter(fmt=formatter)

parse_logger.addHandler(hdlr=file_handler)


def check_vk_requirements(media_file):
    if media_file['type'] in {1, 2}:
        if 400 <= media_file['width'] <= 5000:
            if 350 <= media_file['height'] <= 5000:
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
                    for media in post['files']:
                        if check_vk_requirements(media_file=media):
                            links.add(media['path'])
        else:
            if page == 1:
                parse_logger.error(msg=f"Парсер не посетил ни одной страницы (status_code: {response.status_code})")
            else:
                parse_logger.info(msg=f"Парсер посетил {page - 1} страниц, обнаружил {len(links)} картинок")
            break
    return links


data.set_variables()
stats_before = data.get_db_stats(db_path=data.DB_PATH, get_query=data.GET_STATS)

image_links = get_images_from_2ch_section(url=data.URL, section=data.PARTITION)
data.links_to_db(db_path=data.DB_PATH, query=data.INSERT_QUERY, links=image_links)

stats_after = data.get_db_stats(db_path=data.DB_PATH, get_query=data.GET_STATS)
if not (stats_after[0] - stats_before[0]):
    parse_logger.warning(msg="Запас неиспользованных картинок остался прежним")
else:
    parse_logger.info(f"Запас неиспользованных картинок пополнился на {stats_after[0] - stats_before[0]} штук")
