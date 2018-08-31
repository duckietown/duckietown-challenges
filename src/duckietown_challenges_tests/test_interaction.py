import os
import tempfile

from duckietown_challenges import ChallengeInterfaceEvaluator, ChallengeInterfaceSolution, read_challenge_results
from duckietown_challenges.challenge_evaluator import ChallengeEvaluator
from duckietown_challenges.challenge_solution import ChallengeSolution
from duckietown_challenges.cie_concrete import ChallengeInterfaceEvaluatorConcrete, ChallengeInterfaceSolutionConcrete
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
        cis.set_solution_output_file(FN1, fn, FN1)

        params = cis.get_challenge_parameters()
        assert params[K1] == V1

        challenge_files = cis.get_challenge_files()
        assert FN2 in challenge_files

        cis.set_solution_output_dict({K2: V2})

        # TODO: declare_failure


def test_interaction1():
    S = S1()
    E = E1()
    root = tempfile.mkdtemp()
    cie = ChallengeInterfaceEvaluatorConcrete(root)
    E.prepare(cie)
    cie.after_prepare()
    cis = ChallengeInterfaceSolutionConcrete(root)
    S.run(cis)
    cis.after_run()
    E.score(cie)
    cie.after_score()

    cr = read_challenge_results(root)
    assert cr.scores[SCORE1] == SCORE1_VAL, cr.scores

    # TODO: read scores

    #
    #
    # with get_temp_ci() as ci:
    #     wrap_solution(sol1, ci=ci)
    #     wrap_evaluator(sol1, ci=ci)
    #
    # results = ci.read_evaluation()
    # assert results.status == STATUS_FAILED
