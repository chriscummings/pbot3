import logging

logger = logging.getLogger("pbot-listener")

logging.root.setLevel(logging.NOTSET)

c_handler = logging.StreamHandler()
f_handler = logging.FileHandler('pbot-listener.log')

c_handler.setLevel(logging.NOTSET)
f_handler.setLevel(logging.NOTSET)

c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

logger.addHandler(c_handler)
logger.addHandler(f_handler)