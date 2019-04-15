# coding=utf-8
import json
import math
import os
import re

import decorator

from . import dclogger, InvalidConfiguration


def write_data_to_file(data, filename):
    """
        Writes the data to the given filename.
        If the data did not change, the file is not touched.

    """
    if not isinstance(data, str):
        msg = 'Expected "data" to be a string, not %s.' % type(data).__name__
        raise ValueError(msg)
    if len(filename) > 256:
        msg = 'Invalid argument filename: too long. Did you confuse it with data?'
        raise ValueError(msg)

    filename = expand_all(filename)
    d8n_make_sure_dir_exists(filename)

    if os.path.exists(filename):
        current = open(filename).read()
        if current == data:
            if not 'assets/' in filename:
                dclogger.debug('already up to date %s' % filename)
            return

    tmp = filename + '.tmp'
    with open(tmp, 'w') as f:
        f.write(data)
    os.rename(tmp, filename)
    dclogger.debug('Written to: %s' % filename)


def expand_all(filename):
    """
        Expands ~ and ${ENV} in the string.

        Raises DTConfigException if some environment variables
        are not expanded.

    """
    fn = filename
    fn = os.path.expanduser(fn)
    fn = os.path.expandvars(fn)
    if '$' in fn:
        msg = 'Could not expand all variables in path %r.' % fn
        raise ValueError(msg)
    return fn


def d8n_make_sure_dir_exists(filename):
    """
        Makes sure that the path to file exists, by creating directories.

    """
    dirname = os.path.dirname(filename)

    # dir == '' for current dir
    if dirname != '' and not os.path.exists(dirname):
        d8n_mkdirs_thread_safe(dirname)


def d8n_mkdirs_thread_safe(dst):
    """
        Make directories leading to 'dst' if they don't exist yet.

        This version is thread safe.

    """
    if dst == '' or os.path.exists(dst):
        return
    head, _ = os.path.split(dst)
    if os.sep == ':' and not ':' in head:
        head += ':'
    d8n_mkdirs_thread_safe(head)
    try:
        mode = 511  # 0777 in octal
        os.mkdir(dst, mode)
    except OSError as err:
        if err.errno != 17:  # file exists
            raise


@decorator.decorator
def wrap_config_reader2(f, cls, data: dict, *args, **kwargs):
    """ Decorator for a function that takes a (clsname, dict) """
    # def f2(x, *args, **kwargs):
    if not isinstance(data, dict):
        msg = 'Expected dict, got %s' % data.__repr__()
        raise ValueError(msg)

    def write(d: dict):
        assert isinstance(d, dict)
        try:
            return json.dumps(d, indent=4)
        except:
            # try:
            #     return safe_yaml_dump(d, default_flow_style=False).encode('utf-8')
            # except:
            return str(d)

    data2 = dict(**data)

    try:
        res = f(cls, data2, *args, **kwargs)
    except KeyError as e:
        msg = 'Could not interpret the configuration data using %s:%s()' % (cls.__name__, f.__name__)
        msg += '\nMissing configuration "%s". Specified: %s' % (e.args, list(data))
        msg += '\n\n' + indent(write(data), '  > ') + '\n'
        raise InvalidConfiguration(msg) from e
    except InvalidConfiguration as e:
        msg = 'Could not interpret the configuration data using %s:%s()' % (cls.__name__, f.__name__)
        msg += '\n\n' + indent(write(data), '  > ') + '\n'
        raise InvalidConfiguration(msg) from e
    except BaseException as e:
        msg = 'Could not interpret the configuration data using %s:%s()' % (cls.__name__, f.__name__)
        msg += '\n\n' + indent(write(data), '  > ') + '\n'
        # raise_wrapped(InvalidConfiguration, e, msg, compact=False)
        raise InvalidConfiguration(msg) from e

    if data2:
        msg = 'Unused fields %s ' % list(data2)
        msg += '\n\n' + indent(write(data), '  > ')
        raise InvalidConfiguration(msg)

    return res


def safe_yaml_dump(x, **args):
    import yaml
    s = yaml.safe_dump(x, encoding='utf-8', indent=4, allow_unicode=True, **args)
    return s


def friendly_size(b):
    if b == 0:
        return 'empty'

    if b < 1024:
        return '%d  B' % b

    if b < 1024 * 1024:
        kbs = math.ceil(b / 1024.0)
        return '%d KB' % kbs

    if b < 1024 * 1024 * 1024:
        mbs = math.ceil(b / (1024.0 * 1024.0))
        return '%d MB' % mbs

    gbs = b / (1024.0 * 1024.0 * 1024)
    return '%.2f GB' % gbs


def friendly_size2(b):
    if b == 0:
        return 'empty'

    if b < 1024:
        return '%d  B' % b

    if b < 1024 * 1024:
        kbs = b / 1024.0
        return '%.2f KB' % kbs

    if b < 1024 * 1024 * 1024:
        mbs = b / (1024.0 * 1024.0)
        return '%.2f MB' % mbs

    gbs = b / (1024.0 * 1024.0 * 1024)
    return '%.2f GB' % gbs


def indent(s, prefix: str, first=None):
    s = str(s)

    lines = s.split('\n')
    if not lines:
        return ''

    if first is None:
        first = prefix

    m = max(len(prefix), len(first))

    prefix = ' ' * (m - len(prefix)) + prefix
    first = ' ' * (m - len(first)) + first

    # differnet first prefix
    res = ['%s%s' % (prefix, line.rstrip()) for line in lines]
    res[0] = '%s%s' % (first, lines[0].rstrip())
    return '\n'.join(res)


#
#
# def raise_wrapped(etype, e, msg, compact=False, exc=None, **kwargs):
#     """ Raises an exception of type etype by wrapping
#         another exception "e" with its backtrace and adding
#         the objects in kwargs as formatted by format_obs.
#
#         if compact = False, write the whole traceback, otherwise just str(e).
#
#         exc = output of sys.exc_info()
#     """
#
#     e = raise_wrapped_make(etype, e, msg, compact=compact, **kwargs)
#
#     #     if exc is not None:
#     #         _, _, trace = exc
#     #         raise etype, e.args, trace
#     #     else:
#     raise e
#
#
# def raise_wrapped_make(etype, e, msg, compact=False, **kwargs):
#     """ Constructs the exception to be thrown by raise_wrapped() """
#     assert isinstance(e, BaseException), type(e)
#     assert isinstance(msg, str), type(msg)
#     s = msg
#
#     import sys
#     if sys.version_info[0] >= 3:
#         es = str(e)
#     else:
#         if compact:
#             es = str(e)
#         else:
#             es = traceback.format_exc()
#
#     s += '\n' + indent(es.strip(), '| ')
#
#     return etype(s)


def check_isinstance(ob, expected, **kwargs):
    if not isinstance(ob, expected):
        kwargs['object'] = ob
        raise_type_mismatch(ob, expected, **kwargs)


def raise_type_mismatch(ob, expected, **kwargs):
    """ Raises an exception concerning ob having the wrong type. """
    e = 'Object not of expected type:'
    e += '\n  expected: %s' % str(expected)
    e += '\n  obtained: %s' % str(type(ob))
    # e += '\n' + indent(format_obs(kwargs), ' ')
    raise ValueError(e)



def tag_from_date(d):
    # YYYY-MM-DDTHH:MM:SS[.mmmmmm][+HH:MM].
    s = d.isoformat()

    s = s.replace(':', '_')
    s = s.replace('T', '_')
    s = s.replace('-', '_')
    s = s[:s.index('.')]
    return s


def remove_escapes(s):
    escape = re.compile('\x1b\[..?m')
    return escape.sub("", s)


def get_length_on_screen(s):
    """ Returns the length of s without the escapes """
    return len(remove_escapes(s))


def pad_to_screen_length(s, desired_screen_length,
                         pad=" ", last=None,
                         align_right=False):
    """
        Pads a string so that it will appear of the given size
        on the terminal.

        align_right: aligns right instead of left (default)
    """
    assert isinstance(desired_screen_length, int)
    # todo: assert pad = 1
    current_size = get_length_on_screen(s)

    if last is None:
        last = pad

    if current_size < desired_screen_length:
        nadd = (desired_screen_length - current_size)
        padding = (pad * (nadd - 1))
        if align_right:
            s = last + padding + s
        else:
            s = s + padding + last

    # if debug_padding:
    #     if current_size > desired_screen_length:
    #         T = '(cut)'
    #         s = s[:desired_screen_length - len(T)] + T

    return s
