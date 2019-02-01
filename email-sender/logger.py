import sys
from loguru import logger

import json
from datetime import date, datetime

global stdout_registred
stdout_registred = False

class LoggerProxy:
    def __init__(self, name, min_level='INFO'):
        self.__logger = logger.bind(logger_name=name)
        self.__sinks(self.__logger, name, min_level)

    def debug(self, message, *args, **kwargs):
        self.__logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        self.__logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self.__logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.__logger.error(message, *args, **kwargs)

    @staticmethod
    def __sinks(passed_logger, logger_name, min_level):

        global stdout_registred
        if not stdout_registred:
            stdout_registred = True
            passed_logger.remove()
            passed_logger.add(
                sys.stdout,
                format=
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                    "<level>{level}</level> | "
                    "<cyan>{extra[logger_name]}</cyan> - <level>{message}</level>",
                colorize=True,
                level=min_level)


        passed_logger.add(
                "./logs/{0}.log".format(logger_name),
                format="{time} | {level} | {extra[logger_name]} | {message}",
                rotation="20 MB",
                filter=lambda log_entry: logger_name == log_entry['extra']['logger_name'],
                level=min_level)
