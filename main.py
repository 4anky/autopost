import logging
from os import path

import image_parser
import autopost
import data


logging.basicConfig(level=logging.INFO)

script_name = path.basename(__file__)
main_logger = logging.getLogger(name=script_name)
main_logger.setLevel(level=logging.INFO)

file_handler = logging.FileHandler(filename=f"logs/{path.splitext(script_name)[0]}.log")
formatter = logging.Formatter(fmt="%(asctime)s - %(name)s - %(levelname)s — %(funcName)s:%(lineno)d - %(message)s")
file_handler.setFormatter(fmt=formatter)

main_logger.addHandler(hdlr=file_handler)

data.set_variables()
not_used_number, image = autopost.save_image(url=data.URL, db_path=data.DB_PATH)

if image:
    autopost.add_post(login=data.LOGIN,
                      password=data.PASSWORD,
                      group_id=data.GROUP_ID,
                      image_name=image,
                      message=autopost.hash_tags_from_file(file=data.HT_FILE))
    autopost.delete_image(image_name=image)

if not_used_number < 2000:
    image_links = image_parser.get_images_from_2ch_section(url=data.URL, section=data.PARTITION)
    not_used_now = data.links_to_db(db_path=data.DB_PATH, links=image_links)
    if not_used_now - not_used_number:
        main_logger.warning(msg=f"Банк изображений не пополнился ({not_used_now} штук)")
    else:
        main_logger.info(msg=f"Число изображений в Банке увеличилось с {not_used_number} до {not_used_now} штук")
