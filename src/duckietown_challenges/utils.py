import os

from . import dclogger

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
                dclogger.debug('already up to date %s' % (filename))
            return

    tmp = filename+'.tmp'
    with open(tmp, 'w') as f:
        f.write(data)
    os.rename(tmp, filename)
    dclogger.debug('Written to: %s' % (filename))



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

