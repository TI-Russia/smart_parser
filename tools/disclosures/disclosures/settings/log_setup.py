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
    troubles_fn = 'troubles_%s' % os.path.basename(log_path)
    troubles_path = os.path.join(log_dir, troubles_fn)
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
        }
    }
    return logging_dict


