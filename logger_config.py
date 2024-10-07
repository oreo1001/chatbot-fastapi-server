import logging
import os
from logging.handlers import RotatingFileHandler

def log_config():
    #경로 설정
    real_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(real_path)
    LOGFILE = os.path.join(dir_path, 'app.log')

    #로그 형식 등 설정
    logger = logging.getLogger("log_app")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:  #이거 없으면 두번씩 출력됨 핸들러땜에
        file_handler = RotatingFileHandler(LOGFILE, maxBytes=10000000, backupCount=1)
        # file_handler = logging.FileHandler(LOGFILE)
        stream_handler = logging.StreamHandler() 
        #- %(name)s  log_app
        formatter = logging.Formatter("[%(asctime)s]  %(name)s %(levelname)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger

logger = log_config()