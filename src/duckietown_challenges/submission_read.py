import os

from zuper_commons.types import ZException
from .challenge import SubmissionDescription
from .yaml_utils import read_yaml_file

__all__ = ["CouldNotReadSubInfo", "read_submission_info"]


class CouldNotReadSubInfo(ZException):
    pass


def read_submission_info(fn: str) -> SubmissionDescription:
    """
        Raises CouldNotReadSubInfo

    :param fn: filename
    :return:
    """

    if not os.path.exists(fn):
        msg = "I expected to find the file %s" % fn

        # msg += "\n\nThese are the contents of the directory %s:" % dirname
        # for x in os.listdir(dirname):
        #     msg += "\n- %s" % x

        raise CouldNotReadSubInfo(msg)

    try:
        data = read_yaml_file(fn)
    except BaseException as e:
        msg = "Could not read submission info."
        raise CouldNotReadSubInfo(msg) from e
    try:
        return SubmissionDescription.from_yaml(data)
    except BaseException as e:
        msg = f"Could not read file {fn!r}: {e}"
        raise CouldNotReadSubInfo(msg) from e
