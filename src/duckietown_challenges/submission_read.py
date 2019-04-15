from .yaml_utils import read_yaml_file
from .challenge import SubmissionDescription
import os

class CouldNotReadSubInfo(Exception):
    pass


def read_submission_info(dirname) -> SubmissionDescription:
    """
        Raises CouldNotReadSubInfo

    :param dirname:
    :return:
    """
    if not os.path.exists(dirname):
        msg = 'Could not find directory:\n   %s' % dirname
        raise CouldNotReadSubInfo(msg)

    bn = 'submission.yaml'
    fn = os.path.join(dirname, bn)

    if not os.path.exists(fn):
        msg = 'I expected to find the file %s' % fn

        msg += '\n\nThese are the contents of the directory %s:' % dirname
        for x in os.listdir(dirname):
            msg += '\n- %s' % x

        raise CouldNotReadSubInfo(msg)

    try:
        data = read_yaml_file(fn)
    except BaseException as e:
        msg = 'Could not read submission info.'
        raise CouldNotReadSubInfo(msg) from e
    try:
        return SubmissionDescription.from_yaml(data)
    except BaseException as e:
        msg = 'Could not read file %r: %s' % (fn, e)
        raise CouldNotReadSubInfo(msg) from e
