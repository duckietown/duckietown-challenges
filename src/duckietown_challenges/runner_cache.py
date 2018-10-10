import os
import shutil

from . import dclogger
# cache_max_size_gb = 3
from .utils import friendly_size

cache_dir = '/tmp/duckietown/DT18/evaluator/cache'
cache_dir_by_value = os.path.join(cache_dir, 'by-value', 'sha256hex')

disable_cache = False


def get_file_from_cache(fn, sha256hex):
    if disable_cache:
        dclogger.warning('Forcing cache disabled.')
        msg = 'cache disabled'
        raise KeyError(msg)
    if not os.path.exists(cache_dir_by_value):
        os.makedirs(cache_dir_by_value)
    have = os.path.join(cache_dir_by_value, sha256hex)
    if os.path.exists(have):
        shutil.copy(have, fn)
    else:
        msg = 'Hash not in cache'
        raise KeyError(msg)


def copy_to_cache(fn, sha256hex):
    if disable_cache:
        dclogger.warning('Forcing cache disabled.')
        return

    if not os.path.exists(cache_dir_by_value):
        os.makedirs(cache_dir_by_value)
    have = os.path.join(cache_dir_by_value, sha256hex)
    if not os.path.exists(have):
        msg = 'Copying %s to cache %s' % (friendly_size(os.stat(fn).st_size), have)
        dclogger.debug(msg)
        shutil.copy(fn, have)
