# -*- coding: utf-8 -*-
import os
import errno


def safe_makedir(path):
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise


def get_logging_settings(log_path):
    log_dir = os.path.dirname(log_path)
    safe_makedir(log_dir)
    search_log_file = os.path.join(log_dir, 'search.log')
    logging_dict = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s.%(funcName)s: %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
        },
        'handlers': {
            'null': {
                'class': 'logging.NullHandler',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_path,
                'formatter': 'verbose',
                'maxBytes': 50 * 1024 * 1024,  # 50 Mb
                'backupCount': 5
            },
            'search_log_file_handler': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': search_log_file,
                'formatter': 'verbose',
                'maxBytes': 50 * 1024 * 1024,  # 50 Mb
                'backupCount': 5
            }
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'propagate': False,
                'level': 'INFO',
            },
            'django.db': {
                'handlers': ['file'],
                'propagate': False,
                'level': 'DEBUG',
            },
            'django.request': {
                'handlers': ['file'],
                'propagate': False,
                'level': 'ERROR'
            },
            'django.security': {
                'handlers': ['file'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['file'],
                'propagate': False,
                'level': 'WARNING'
            },
            'django.security.DisallowedHost': {
                'handlers': ['file'],
                'propagate': False,
            },
           'declarations.views': {
               'handlers': ['search_log_file_handler'],
               'propagate': False,
               'level': 'DEBUG',
           },
        }
    }
    return logging_dict


