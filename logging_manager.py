import logging.config
import logging

config_dict = {
    'version': 1,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': logging.DEBUG,
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'filename': 'app.log',
            'level': logging.INFO,
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console'],
            'level': logging.DEBUG,
            'propagate': False
        },
    'service.api_test': {
            'handlers': ['console'],
            'level': logging.DEBUG,
            'propagate': False
        },
    'service': {
            'handlers': ['console'],
            'level': logging.DEBUG,
            'propagate': False
        }
    }
}
logging.config.dictConfig(config_dict)

def log_function(func):
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Entering: {func.__name__} with args: {args} kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger.debug(f"Exiting: {func.__name__} with result: {result}")
        return result
    return wrapper
