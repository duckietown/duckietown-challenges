import math
import os
import shutil
import sys
import tempfile
import time
import traceback
from collections import namedtuple

from . import dclogger, ENV_CHALLENGE_STEP_NAME
from .constants import CHALLENGE_DESCRIPTION_YAML, CHALLENGE_SOLUTION_OUTPUT_YAML, CHALLENGE_SOLUTION_OUTPUT_DIR, \
    CHALLENGE_EVALUATION_OUTPUT_DIR, CHALLENGE_DESCRIPTION_DIR, ChallengeResultsStatus, CHALLENGE_PREVIOUS_STEPS_DIR, \
    ENV_CHALLENGE_NAME
from .exceptions import InvalidSubmission, InvalidEvaluator, InvalidEnvironment
from .solution_interface import ChallengeInterfaceSolution, ChallengeInterfaceEvaluator
from .utils import raise_wrapped, d8n_make_sure_dir_exists
from .yaml_utils import read_yaml_file, write_yaml

ChallengeFile = namedtuple('ChallengeFile', 'basename from_file contents description')
ReportedScore = namedtuple('ReportedScore', 'name value description')


def check_valid_basename(s):
    pass  # TODO


class FS(object):
    def __init__(self):
        self.files = {}

    def add_from_data(self, basename, contents, description):
        if basename in self.files:
            msg = 'Already know %r' % basename
            raise ValueError(msg)

        self.files[basename] = ChallengeFile(basename, None, contents, description)

    def add(self, basename, from_file, description):
        if not os.path.exists(from_file):
            msg = 'The file does not exist: %s' % from_file
            raise ValueError(msg)

        check_valid_basename(basename)

        if basename in self.files:
            msg = 'Already know %r' % basename
            raise ValueError(msg)

        self.files[basename] = ChallengeFile(basename, from_file, None, description)

    def write(self, dest):
        rfs = list(self.files.values())

        for rf in rfs:
            out = os.path.join(dest, rf.basename)
            d8n_make_sure_dir_exists(out)

            if rf.from_file:
                shutil.copy(rf.from_file, out)
            else:
                with open(out, 'wb') as f:
                    f.write(rf.contents)


class ChallengeInterfaceSolutionConcrete(ChallengeInterfaceSolution):

    def __init__(self, root):
        self.root = root

        self.solution_output_files = FS()
        self.solution_output_dict = None
        self.failure_declared = False
        self.failure_declared_msg = False

    def get_tmp_dir(self):
        return tempfile.mkdtemp()

    def get_challenge_parameters(self):
        fn = os.path.join(self.root, CHALLENGE_DESCRIPTION_YAML)
        return read_yaml_file(fn)

    def get_challenge_files(self):
        d = os.path.join(self.root, CHALLENGE_DESCRIPTION_DIR)
        return sorted(os.listdir(d))

    def get_challenge_file(self, basename):
        d = os.path.join(self.root, CHALLENGE_DESCRIPTION_DIR)
        fn = os.path.join(d, basename)
        if not os.path.exists(fn):
            msg = 'Could not get file %r' % fn
            raise ValueError(msg)
        return fn

    def set_solution_output_dict(self, data):
        if not isinstance(data, dict):
            msg = 'data must be a dict, got %s' % data
            raise ValueError(msg)
        self.solution_output_dict = data

    def declare_failure(self, msg=None):
        self.failure_declared = True
        self.failure_declared_msg = msg

    def set_solution_output_file(self, basename, from_file, description=None):
        try:
            self.solution_output_files.add(basename, from_file, description)
        except ValueError as e:
            msg = 'Invalid set_solution_output_file()'
            raise_wrapped(InvalidSubmission, e, msg)

    def set_solution_output_file_from_data(self, basename, contents, description=None):
        try:
            self.solution_output_files.add_from_data(basename, contents, description)
        except ValueError as e:
            msg = 'Invalid set_solution_output_file()'
            raise_wrapped(InvalidSubmission, e, msg)

    def info(self, s):
        dclogger.info('solution:%s' % s)

    def error(self, s):
        dclogger.error('solution:%s' % s)

    def debug(self, s):
        dclogger.debug('solution:%s' % s)

    # def after_run(self):

    def _write_files(self):
        d = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_DIR)
        self.solution_output_files.write(d)

    def wait_for_preparation(self):
        fn = os.path.join(self.root, CHALLENGE_DESCRIPTION_YAML)
        return wait_for_file(fn, timeout=TIMEOUT_PREPARATION, wait=1)

    def get_challenge_name(self):
        try:
            return os.environ[ENV_CHALLENGE_NAME]
        except KeyError as e:
            raise InvalidEnvironment(str(e))

    def get_current_step(self):
        """ Returns the current step. """
        try:
            return os.environ[ENV_CHALLENGE_STEP_NAME]
        except KeyError as e:
            raise InvalidEnvironment(str(e))

    def get_completed_steps(self):
        """ Returns the previous steps as a list of string """
        p = os.path.join(self.root, CHALLENGE_PREVIOUS_STEPS_DIR)
        if not os.path.exists(p):
            msg = 'Directory not found %s' % p
            raise InvalidEnvironment(msg)
        dirnames = os.listdir(p)
        return list(dirnames)

    def get_completed_step_solution_files(self, step_name):
        """ Returns a list of names for the files completed in a previous step. """
        if step_name not in self.get_completed_steps():
            msg = 'No step "%s".' % step_name
            raise KeyError(msg)

        return get_completed_step_solution_files(self.root, step_name)

    def get_completed_step_solution_file(self, step_name, basename):
        """ Returns a filename for one of the files completed in a previous step."""
        return get_completed_step_solution_file(self.root, step_name, basename)


TIMEOUT_PREPARATION = 6000
TIMEOUT_SOLUTION = 6000


def get_completed_step_solution_files(root, step_name):
    d0 = os.path.join(root, CHALLENGE_PREVIOUS_STEPS_DIR)
    if not os.path.exists(d0):
        msg = 'Could not find %s' % d0
        raise InvalidEnvironment(msg)

    dir_step = os.path.join(d0, step_name)
    if not os.path.exists(dir_step):
        msg = 'No step "%s".' % step_name
        raise KeyError(msg)
    #
    # if not os.path.exists(d1):
    #     assert os.path.islink(d1), d1
    #     dest = os.readlink(d1)
    #     msg = 'The path %s is a symlink to %s but it does not exist.' % (d1, dest)
    #     raise InvalidEnvironment(msg)

    d = os.path.join(dir_step, CHALLENGE_SOLUTION_OUTPUT_DIR)
    if not os.path.exists(d):
        msg = 'Could not find %s' % d
        raise InvalidEnvironment(msg)

    return list(os.listdir(d))


def get_completed_step_solution_file(root, step_name, basename):
    available = get_completed_step_solution_files(root, step_name)

    # if basename not in available:
    #     msg = 'No file %r' % basename
    #     raise KeyError(msg)

    fn = os.path.join(root, CHALLENGE_PREVIOUS_STEPS_DIR, step_name, CHALLENGE_SOLUTION_OUTPUT_DIR, basename)
    if not os.path.exists(fn):
        msg = 'Cannot find %s; know %s' % (fn, available)
        raise KeyError(msg)
    return fn


class Timeout(Exception):
    pass


def wait_for_file(fn, timeout, wait):
    t0 = time.time()
    while not os.path.exists(fn):
        passed = int(time.time() - t0)
        to_wait = timeout - passed
        dclogger.debug('Output %s not ready yet (%s secs passed, will wait %s secs more)' % (fn, passed, to_wait))
        if time.time() > t0 + timeout:
            msg = 'Timeout of %s while waiting for %s.' % (timeout, fn)
            raise Timeout(msg)
        time.sleep(wait)


class ChallengeInterfaceEvaluatorConcrete(ChallengeInterfaceEvaluator):

    def __init__(self, root='/'):
        self.root = root

        self.challenge_files = FS()  # -> ChallengeFile
        self.parameters = None

        self.evaluation_files = FS()  # -> ChallengeFile
        self.scores = {}  # str -> ReportedScore

    def set_challenge_parameters(self, data):
        assert isinstance(data, dict)
        self.parameters = data

    def get_tmp_dir(self):
        return tempfile.mkdtemp()

    # preparation

    def set_challenge_file(self, basename, from_file, description=None):
        try:
            self.challenge_files.add(basename, from_file, description)
        except ValueError as e:
            msg = 'Invalid set_challenge_file()'
            raise_wrapped(InvalidEvaluator, e, msg)

    def wait_for_solution(self):
        fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_YAML)
        try:
            return wait_for_file(fn, timeout=TIMEOUT_SOLUTION, wait=1)
        except Timeout as e:
            msg = 'Time out: %s' % e
            raise InvalidSubmission(msg)

    def get_solution_output_dict(self):
        fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_YAML)
        return read_yaml_file(fn)

    def get_solution_output_file(self, basename):
        fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_DIR, basename)
        if not os.path.exists(fn):
            msg = 'Could not find file %r' % fn
            raise InvalidSubmission(msg)
        return fn

    def get_solution_output_files(self):
        d = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_DIR)
        fns = list(os.listdir(d))
        return fns

    def set_score(self, name, value, description=None):
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                msg = 'Invalid value %r for score %r: we do not allow infinity or NaN.' % (value, name)
                raise ValueError(msg)

        import numpy as np
        if type(value) is np.ndarray:
            msg = 'Please use regular floats and not numpy array. Invalid value for %s: %s' % (name, value)
            raise Exception(msg)

        if name in self.scores:
            msg = 'Already know score %r' % name
            raise InvalidEvaluator(msg)

        self.scores[name] = ReportedScore(name, value, description)

    def set_evaluation_file(self, basename, from_file, description=None):
        try:
            self.evaluation_files.add(basename, from_file, description)
        except ValueError as e:
            msg = 'Invalid set_evaluation_file()'
            raise_wrapped(InvalidEvaluator, e, msg)

    def set_evaluation_file_from_data(self, basename, contents, description=None):
        try:
            self.evaluation_files.add_from_data(basename, contents, description)
        except ValueError as e:
            msg = 'Invalid set_evaluation_file_from_data()'
            raise_wrapped(InvalidEvaluator, e, msg)

    def info(self, s):
        dclogger.info('evaluation: %s' % s)

    def error(self, s):
        dclogger.error('evaluation: %s' % s)

    def debug(self, s):
        dclogger.debug('evaluation: %s' % s)

    def after_prepare(self):
        if self.parameters is None:
            msg = 'Parameters not set. Evaluator must use set_challenge_parameters().'
            raise InvalidEvaluator(msg)  # XXX

        d = os.path.join(self.root, CHALLENGE_DESCRIPTION_DIR)
        self.challenge_files.write(d)

        fn = os.path.join(self.root, CHALLENGE_DESCRIPTION_YAML)
        write_yaml(self.parameters, fn)

    def after_score(self):
        # self.evaluation_files = {}  # -> ChallengeFile
        # self.scores = {}  # str -> ReportedScore
        if not self.scores:
            msg = 'No scores created'
            raise InvalidEvaluator(msg)  # XXX

        d = os.path.join(self.root, CHALLENGE_EVALUATION_OUTPUT_DIR)
        self.evaluation_files.write(d)

        status = ChallengeResultsStatus.SUCCESS
        msg = None
        scores = {}
        for k, v in self.scores.items():
            scores[k] = v.value
        cr = ChallengeResults(status, msg, scores)

        declare_challenge_results(self.root, cr)

    def get_challenge_name(self):
        try:
            return os.environ[ENV_CHALLENGE_NAME]
        except KeyError as e:
            raise InvalidEnvironment(str(e))

    def get_current_step(self):
        """ Returns the current step. """
        try:
            return os.environ[ENV_CHALLENGE_STEP_NAME]
        except KeyError as e:
            raise InvalidEnvironment(str(e))

    def get_completed_steps(self):
        """ Returns the previous steps as a list of string """
        p = os.path.join(self.root, CHALLENGE_PREVIOUS_STEPS_DIR)
        if not os.path.exists(p):
            msg = 'Directory not found %s' % p
            raise InvalidEnvironment(msg)  # XXX invalid runner...
        dirnames = os.listdir(p)
        return list(dirnames)

    def get_completed_step_evaluation_files(self, step_name):
        """ Returns a list of names for the files completed in a previous step. """
        if step_name not in self.get_completed_steps():
            msg = 'No step %r' % step_name
            raise KeyError(msg)

        return get_completed_step_evaluation_files(self.root, step_name)
        # # XXX
        # d = os.path.join(self.root, CHALLENGE_PREVIOUS_STEPS_DIR, step_name, CHALLENGE_EVALUATION_OUTPUT_DIR)
        # return list(os.listdir(d))

    def get_completed_step_evaluation_file(self, step_name, basename):
        """ Returns a filename for one of the files completed in a previous step."""
        # if basename not in self.get_completed_step_evaluation_files(step_name):
        #     msg = 'No file %r' % basename
        #     raise KeyError(msg)
        # fn = os.path.join(self.root, CHALLENGE_PREVIOUS_STEPS_DIR, step_name, CHALLENGE_EVALUATION_OUTPUT_DIR, basename)
        # return fn

        return get_completed_step_evaluation_file(self.root, step_name, basename)


def get_completed_step_evaluation_files(root, step_name):
    d0 = os.path.join(root, CHALLENGE_PREVIOUS_STEPS_DIR)
    if not os.path.exists(d0):
        msg = 'Could not find %s' % d0
        raise InvalidEnvironment(msg)

    d_step = os.path.join(d0, step_name)
    if not os.path.exists(d_step):
        msg = 'No step "%s": dir %s does not exist.' % (step_name, d_step)
        raise KeyError(msg)
    #
    # if not os.path.exists(d1):
    #     assert os.path.islink(d1), d1
    #     dest = os.readlink(d1)
    #     msg = 'The path %s is a symlink to %s but it does not exist.' % (d1, dest)
    #     raise InvalidEnvironment(msg)

    d = os.path.join(d_step, CHALLENGE_EVALUATION_OUTPUT_DIR)
    if not os.path.exists(d):
        msg = 'Could not find dir %s' % d
        raise InvalidEnvironment(msg)

    return list(os.listdir(d))


def get_completed_step_evaluation_file(root, step_name, basename):
    available = get_completed_step_evaluation_files(root, step_name)

    # if basename not in available:
    #     msg = 'No file %r' % basename
    #     raise KeyError(msg)

    fn = os.path.join(root, CHALLENGE_PREVIOUS_STEPS_DIR, step_name, CHALLENGE_EVALUATION_OUTPUT_DIR, basename)
    if not os.path.exists(fn):
        msg = 'Cannot find %s; know %s' % (fn, available)
        raise KeyError(msg)
    return fn


from .challenge_results import ChallengeResults, declare_challenge_results

# from evaluator
SPECIAL_ABORT = 'abort'
# from submission
SPECIAL_INVALID_ENVIRONMENT = 'invalid-environment'
SPECIAL_INVALID_EVALUATOR = 'invalid-evaluator'
SPECIAL_INVALID_SUBMISSION = 'invalid-submission'


def formate(e):
    return traceback.format_exc()

def wrap_evaluator(evaluator, root='/'):
    from .col_logging import setup_logging_color
    setup_logging_color()

    def declare(status, message):
        if status != ChallengeResultsStatus.SUCCESS:
            msg = 'declare %s:\n%s' % (status, message)
            dclogger.error(msg)
        else:
            dclogger.info('Completed.')
        cr = ChallengeResults(status, message, {})
        declare_challenge_results(root, cr)
        sys.exit(0)

    cie = ChallengeInterfaceEvaluatorConcrete(root=root)

    try:
        try:
            evaluator.prepare(cie)
        except BaseException as e:
            msg = 'Preparation aborted:\n%s' % formate(e)
            cie.set_challenge_parameters({SPECIAL_ABORT: msg})
            raise
        finally:
            cie.after_prepare()

        cie.wait_for_solution()

        out = cie.get_solution_output_dict()

        if SPECIAL_INVALID_ENVIRONMENT in out:
            raise InvalidEnvironment(out[SPECIAL_INVALID_ENVIRONMENT])
        elif SPECIAL_INVALID_EVALUATOR in out:
            raise InvalidEvaluator(out[SPECIAL_INVALID_EVALUATOR])
        elif SPECIAL_INVALID_SUBMISSION in out:
            raise InvalidSubmission(out[SPECIAL_INVALID_SUBMISSION])
        else:
            evaluator.score(cie)
            cie.after_score()

    # failure
    except InvalidSubmission as e:
        msg = 'InvalidSubmission:\n%s' % formate(e)
        declare(ChallengeResultsStatus.FAILED, msg)

    # error of evaluator
    except InvalidEvaluator as e:
        msg = 'InvalidEvaluator:\n%s' % formate(e)
        declare(ChallengeResultsStatus.ERROR, msg)

    # error of environment (not distinguished so far)

    except InvalidEnvironment as e:
        msg = 'InvalidEnvironment:\n%s' % formate(e)
        declare(ChallengeResultsStatus.ERROR, msg)

    except BaseException as e:
        msg = 'Unexpected exception:\n%s' % formate(e)
        declare(ChallengeResultsStatus.ERROR, msg)


def wrap_scorer(evaluator, root='/'):
    from .col_logging import setup_logging_color
    setup_logging_color()

    def declare(status, message):
        if status != ChallengeResultsStatus.SUCCESS:
            msg = 'declare %s:\n%s' % (status, message)
            dclogger.error(msg)
        else:
            dclogger.info('Completed.')
        cr = ChallengeResults(status, message, {})
        declare_challenge_results(root, cr)
        sys.exit(0)

    cie = ChallengeInterfaceEvaluatorConcrete(root=root)

    try:

        evaluator.score(cie)
        cie.after_score()

    # failure
    except InvalidSubmission as e:
        msg = 'InvalidSubmission:\n%s' % formate(e)
        declare(ChallengeResultsStatus.FAILED, msg)

    # error of evaluator
    except InvalidEvaluator as e:
        msg = 'InvalidEvaluator:\n%s' % formate(e)
        declare(ChallengeResultsStatus.ERROR, msg)

    # error of environment (not distinguished so far)

    except InvalidEnvironment as e:
        msg = 'InvalidEnvironment:\n%s' % formate(e)
        declare(ChallengeResultsStatus.ERROR, msg)

    except BaseException as e:
        msg = 'Unexpected exception:\n%s' % formate(e)
        declare(ChallengeResultsStatus.ERROR, msg)


def wrap_solution(solution, root='/'):
    from .col_logging import setup_logging_color
    setup_logging_color()
    cis = ChallengeInterfaceSolutionConcrete(root=root)
    try:

        try:
            cis.get_challenge_name()
            cis.get_current_step()
        except InvalidEnvironment:
            raise
        except BaseException as e:
            msg = 'Invalid environment: %s' % formate(e)
            raise InvalidEnvironment(msg)

        try:
            cis.wait_for_preparation()
        except Timeout as e:
            msg = 'Timeout while waiting for evaluator: %s' % e
            raise InvalidEvaluator(msg)

        parameters = cis.get_challenge_parameters()
        if SPECIAL_ABORT in parameters:
            msg = 'I will not run solution because evaluator has aborted: \n%s' % parameters[SPECIAL_ABORT]
            raise InvalidEvaluator(msg)

        try:
            solution.run(cis)
        except (InvalidSubmission, InvalidEnvironment, InvalidEvaluator):
            raise
        except BaseException as e:
            msg = "Uncaught exception in solution:\n%s" % formate(e)
            raise InvalidSubmission(msg)

        if cis.failure_declared:
            msg = "Submission declares failure:\n%s" % cis.failure_declared_msg
            raise InvalidSubmission(msg)

        if cis.solution_output_dict is None:
            msg = 'solution_output_dict not set. Solution must use set_solution_output_dict({}).'
            raise InvalidSubmission(msg)

    except InvalidEnvironment as e:
        msg = 'InvalidEnvironment:\n%s' % formate(e)
        cis.error(msg)
        cis.set_solution_output_dict({SPECIAL_INVALID_ENVIRONMENT: msg})
    except InvalidEvaluator as e:
        msg = 'InvalidEvaluator:\n%s' % formate(e)
        cis.error(msg)
        cis.set_solution_output_dict({SPECIAL_INVALID_EVALUATOR: msg})
    except InvalidSubmission as e:
        msg = 'Invalid solution:\n%s' % formate(e)
        cis.error(msg)
        cis.set_solution_output_dict({SPECIAL_INVALID_SUBMISSION: msg})
    except BaseException as e:
        msg = 'Uncaught exception: invalid wrap_evaluator:\n%s' % formate(e)
        cis.error(msg)
        cis.set_solution_output_dict({SPECIAL_INVALID_ENVIRONMENT: msg})
    finally:
        fn = os.path.join(cis.root, CHALLENGE_SOLUTION_OUTPUT_YAML)
        write_yaml(cis.solution_output_dict, fn)
        cis._write_files()
