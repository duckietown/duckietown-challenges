import os
import shutil
import tempfile
import time
import traceback
from collections import namedtuple

from . import dclogger
from .constants import CHALLENGE_DESCRIPTION_YAML, CHALLENGE_SOLUTION_OUTPUT_YAML, CHALLENGE_SOLUTION_OUTPUT_DIR, \
    CHALLENGE_EVALUATION_OUTPUT_DIR, CHALLENGE_DESCRIPTION_DIR
from .utils import d8n_make_sure_dir_exists
from .yaml_utils import read_yaml_file, write_yaml


from .solution_interface import ChallengeInterfaceSolution, ChallengeInterfaceEvaluator

ChallengeFile = namedtuple('ChallengeFile', 'basename from_file description')
ReportedScore = namedtuple('ReportedScore', 'name value description')


def check_valid_basename(s):
    pass  # TODO


class FS(object):
    def __init__(self):
        self.files = {}

    def add(self, basename, from_file, description):
        if not os.path.exists(from_file):
            msg = 'The file does not exist: %s' % from_file
            raise ValueError(msg)

        check_valid_basename(basename)

        if basename in self.files:
            msg = 'Already know %r' % basename
            raise ValueError(msg)

        self.files[basename] = ChallengeFile(basename, from_file, description)

    def write(self, dest):
        rfs = list(self.files.values())

        for rf in rfs:
            out = os.path.join(dest, rf.basename)
            d8n_make_sure_dir_exists(out)
            shutil.copy(rf.from_file, out)


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

    def set_solution_output_dict(self, data):
        self.solution_output_dict = data

    def declare_failure(self, data, msg=None):
        self.failure_declared = True
        self.failure_declared_msg = msg

    def set_solution_output_file(self, basename, from_file, description):
        self.solution_output_files.add(basename, from_file, description)

    def info(self, s):
        dclogger.info(s)

    def error(self, s):
        dclogger.error(s)

    def debug(self, s):
        dclogger.debug(s)

    def after_run(self):
        if not self.solution_output_dict:
            msg = 'solution_output_dict not set.'
            raise Exception(msg)  # XXX
        else:
            fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_YAML)
            write_yaml(self.solution_output_dict, fn)

        d = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_DIR)
        self.solution_output_files.write(d)

    def wait_for_preparation(self):
        fn = os.path.join(self.root, CHALLENGE_DESCRIPTION_YAML)
        return wait_for_file(fn, timeout=10, wait=1)


def wait_for_file(fn, timeout, wait):
    t0 = time.time()
    while not os.path.exists(fn):
        dclogger.debug('Output %s not ready yet' % fn)
        if time.time() - t0 > timeout:
            msg = 'Timeout.'
            raise Exception(msg)
        time.sleep(wait)


class ChallengeInterfaceEvaluatorConcrete(ChallengeInterfaceEvaluator):

    def __init__(self, root='/'):
        self.root = root

        self.challenge_files = FS()  # -> ChallengeFile
        self.parameters = None

        self.evaluation_files = FS()  # -> ChallengeFile
        self.scores = {}  # str -> ReportedScore

    def set_challenge_parameters(self, data):
        self.parameters = data

    def get_tmp_dir(self):
        return tempfile.mkdtemp()

    # preparation

    def set_challenge_file(self, basename, from_file, description=None):
        self.challenge_files.add(basename, from_file, description)

    def wait_for_solution(self):
        fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_YAML)
        return wait_for_file(fn, timeout=10, wait=1)

    def get_solution_output_dict(self):
        fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_YAML)
        return read_yaml_file(fn)

    def get_solution_output_file(self, basename):
        fn = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_DIR, basename)
        if not os.path.exists(fn):
            msg = 'Could not find file %r' % fn
            raise Exception(msg)
        return fn

    def get_solution_output_files(self):
        d = os.path.join(self.root, CHALLENGE_SOLUTION_OUTPUT_DIR)
        fns = list(os.listdir(d))
        return fns

    def set_score(self, name, value, description=None):
        if name in self.scores:
            msg = 'Already know score %r' % name
            raise ValueError(msg)

        self.scores[name] = ReportedScore(name, value, description)

    def set_evaluation_file(self, basename, from_file, description):
        self.evaluation_files.add(basename, from_file, description)

    def info(self, s):
        dclogger.info(s)

    def error(self, s):
        dclogger.error(s)

    def debug(self, s):
        dclogger.debug(s)

    def after_prepare(self):
        if not self.parameters:
            msg = 'Parameters not set.'
            raise Exception(msg)  # XXX

        d = os.path.join(self.root, CHALLENGE_DESCRIPTION_DIR)
        self.challenge_files.write(d)

        fn = os.path.join(self.root, CHALLENGE_DESCRIPTION_YAML)
        write_yaml(self.parameters, fn)
    

    def after_score(self):
        # self.evaluation_files = {}  # -> ChallengeFile
        # self.scores = {}  # str -> ReportedScore
        if not self.scores:
            msg = 'No scores created'
            raise Exception(msg)  # XXX

        d = os.path.join(self.root, CHALLENGE_EVALUATION_OUTPUT_DIR)
        self.evaluation_files.write(d)

        status = 'success'
        msg = None
        scores = {}
        for k, v in self.scores.items():
            scores[k] = v.value
        cr = ChallengeResults(status, msg, scores)

        declare_challenge_results(self.root, cr)


from .challenge_results import ChallengeResults, declare_challenge_results


def wrap_evaluator(evaluator, cie=None):
    if cie is None:
        root = '/'
        cie = ChallengeInterfaceEvaluatorConcrete(root=root)

    try:
        evaluator.prepare(cie)
    except Exception as e:
        dclogger.error(traceback.format_exc(e))
    else:
        cie.after_prepare()

    cie.wait_for_solution()

    try:
        evaluator.score(cie)
    except Exception as e:
        dclogger.error(traceback.format_exc(e))
    else:
        cie.after_score()


def wrap_solution(solution, cis=None):
    if cis is None:
        root = '/'
        cis = ChallengeInterfaceSolutionConcrete(root=root)

    cis.wait_for_preparation()

    try:
        solution.run(cis)
    except Exception as e:
        dclogger.error(traceback.format_exc(e))

    cis.after_run()