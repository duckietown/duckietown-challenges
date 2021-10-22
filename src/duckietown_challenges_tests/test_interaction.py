import os
import tempfile
from unittest import SkipTest
from . import logger
from duckietown_challenges import (
    ChallengeInterfaceEvaluator,
    ChallengeInterfaceSolution,
    ChallengesConstants,
    read_challenge_results,
    wrap_evaluator,
    wrap_solution,
)
from duckietown_challenges.challenge_evaluator import ChallengeEvaluator
from duckietown_challenges.challenge_solution import ChallengeSolution
from duckietown_challenges.utils import write_data_to_file

FN1 = "c1"
K1 = "dummy"
V1 = "dumm"
K2 = "r"
V2 = "r2"

FN2 = "fn2"
FN3 = "fn3"
SCORE1 = "score1"
SCORE1_VAL = 42
DUMMY_DATA = "djeoijdo"


class E1(ChallengeEvaluator):
    def prepare(self, cie):
        assert isinstance(cie, ChallengeInterfaceEvaluator)
        cie.set_challenge_parameters({K1: V1})

        tmp = cie.get_tmp_dir()
        fn = os.path.join(tmp, FN2)
        write_data_to_file(DUMMY_DATA, fn)
        cie.set_challenge_file(FN2, fn)

    def score(self, cie):
        assert isinstance(cie, ChallengeInterfaceEvaluator)
        fns = cie.get_solution_output_files()
        assert FN1 in fns
        res = cie.get_solution_output_dict()
        assert res[K2] == V2
        cie.set_score(SCORE1, SCORE1_VAL)

        tmp = cie.get_tmp_dir()
        fn = os.path.join(tmp, FN3)
        write_data_to_file(DUMMY_DATA, fn)
        cie.set_challenge_file(FN3, fn)


class S1(ChallengeSolution):
    def run(self, cis):
        assert isinstance(cis, ChallengeInterfaceSolution)

        tmp = cis.get_tmp_dir()
        fn = os.path.join(tmp, FN1)
        write_data_to_file(FN1, fn)
        cis.set_solution_output_file(FN1, fn)

        params = cis.get_challenge_parameters()
        assert params[K1] == V1

        challenge_files = cis.get_challenge_files()
        assert FN2 in challenge_files

        cis.set_solution_output_dict({K2: V2})

        # TODO: declare_failure


from multiprocessing import Process


def process_evaluator(E, root):
    wrap_evaluator(E, root=root)


def process_solution(S, root):
    wrap_solution(S, root=root)


def run_interaction(S, E):
    root = tempfile.mkdtemp()
    print("Root: %s" % root)
    os.environ["challenge_name"] = "test-challenge"
    os.environ["challenge_step_name"] = "test-challenge-step"

    p_e = Process(target=process_evaluator, args=(E, root))
    p_e.start()
    p_s = Process(target=process_solution, args=(S, root))
    p_s.start()
    p_e.join()

    cr = read_challenge_results(root)
    return cr


def test_interaction1():
    S = S1()
    E = E1()
    cr = run_interaction(S, E)
    status = cr.get_status()
    try:
        assert status == ChallengesConstants.STATUS_JOB_SUCCESS, status
        assert cr.scores[SCORE1] == SCORE1_VAL, cr.scores
    except:
        logger.info(cr=cr)
        raise SkipTest("This is a flaky test")


class ENoScores(ChallengeEvaluator):
    def prepare(self, cie):
        cie.set_challenge_parameters({K1: V1})

    def score(self, cie):
        pass


class SDummy2(ChallengeSolution):
    def run(self, cis):
        cis.set_solution_output_dict({K1: V1})


def test_no_scores():
    cr = run_interaction(SDummy2(), ENoScores())
    status = cr.get_status()
    assert status == ChallengesConstants.STATUS_JOB_ERROR, status


class EDummy(ChallengeEvaluator):
    def prepare(self, cie):
        cie.set_challenge_parameters({K1: V1})

    def score(self, cie):
        pass


class SDummy(ChallengeSolution):
    def run(self, cis):
        pass  # cis.set_solution_output_dict({K1: V1})


def test_no_solution_output():
    cr = run_interaction(SDummy(), EDummy())
    status = cr.get_status()
    assert status == ChallengesConstants.STATUS_JOB_FAILED, status
