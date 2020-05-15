import configparser

import synceyes


config = configparser.ConfigParser()
config.read(filenames="config/config.ini")

main_logger = synceyes.create_logger()

Database = synceyes.Database(database=config['database'])
Poster = synceyes.Poster(database=config['database'], vk=config['vk'], site=config['site'], local=config['local'])
Parser = synceyes.Parser(site=config['site'])

not_used_number, is_saved = Poster.save_image()

if is_saved:
    Poster.add_post()
    Poster.delete_image()

if not_used_number < 20_000:
    not_used_now = Database.links_to_db(links=Parser.get_images())
    if not_used_now - not_used_number:
        main_logger.info(msg=f"Число изображений в Банке увеличилось с {not_used_number} до {not_used_now} штук")
    else:
        main_logger.warning(msg=f"Банк изображений не пополнился ({not_used_now} штук)")
