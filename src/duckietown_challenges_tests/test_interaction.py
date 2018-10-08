import os
import tempfile

from comptests import run_module_tests

from duckietown_challenges import ChallengeInterfaceEvaluator, ChallengeInterfaceSolution, read_challenge_results, \
    ChallengeResultsStatus, wrap_solution, wrap_evaluator
from duckietown_challenges.challenge_evaluator import ChallengeEvaluator
from duckietown_challenges.challenge_solution import ChallengeSolution
from duckietown_challenges.utils import write_data_to_file

FN1 = 'c1'
K1 = 'dummy'
V1 = 'dumm'
K2 = 'r'
V2 = 'r2'

FN2 = 'fn2'
FN3 = 'fn3'
SCORE1 = 'score1'
SCORE1_VAL = 42
DUMMY_DATA = 'djeoijdo'


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


def run_interaction(S, E):
    root = tempfile.mkdtemp()
    print('Root: %s' % root)

    def process_evaluator():
        wrap_evaluator(E, root=root)

    def process_solution():
        wrap_solution(S, root=root)

    p_e = Process(target=process_evaluator)
    p_e.start()
    p_s = Process(target=process_solution)
    p_s.start()
    p_e.join()

    cr = read_challenge_results(root)
    return cr


def test_interaction1():
    S = S1()
    E = E1()
    cr = run_interaction(S, E)
    assert cr.get_status() == ChallengeResultsStatus.SUCCESS
    assert cr.scores[SCORE1] == SCORE1_VAL, cr.scores


def test_no_scores():
    class ENoScores(ChallengeEvaluator):

        def prepare(self, cie):
            cie.set_challenge_parameters({K1: V1})

        def score(self, cie):
            pass

    class SDummy(ChallengeSolution):

        def run(self, cis):
            cis.set_solution_output_dict({K1: V1})

    cr = run_interaction(SDummy(), ENoScores())
    assert cr.get_status() == ChallengeResultsStatus.ERROR


def test_no_solution_output():
    class EDummy(ChallengeEvaluator):

        def prepare(self, cie):
            cie.set_challenge_parameters({K1: V1})

        def score(self, cie):
            pass

    class SDummy(ChallengeSolution):

        def run(self, cis):
            pass  # cis.set_solution_output_dict({K1: V1})

    cr = run_interaction(SDummy(), EDummy())
    assert cr.get_status() == ChallengeResultsStatus.FAILED


if __name__ == '__main__':
    run_module_tests()
