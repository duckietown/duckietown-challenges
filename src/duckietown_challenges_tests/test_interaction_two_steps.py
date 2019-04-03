import json
import os
import shutil
from multiprocessing import Process

from comptests import comptest, run_module_tests

from duckietown_challenges import wrap_evaluator, wrap_solution, read_challenge_results, tempfile, ChallengeEvaluator, \
    ChallengeInterfaceEvaluator, ChallengeSolution, ChallengeInterfaceSolution, ENV_CHALLENGE_NAME, \
    ENV_CHALLENGE_STEP_NAME, CHALLENGE_PREVIOUS_STEPS_DIR


def set_step(sname):
    os.environ[ENV_CHALLENGE_NAME] = 'dummy'
    os.environ[ENV_CHALLENGE_STEP_NAME] = sname


def run_interaction_two_steps(step1_name, S1, E1, step2_name, S2, E2):
    root1 = tempfile.mkdtemp()
    os.makedirs(os.path.join(root1, CHALLENGE_PREVIOUS_STEPS_DIR))
    print('Root: %s' % root1)

    def step1_evaluator():
        set_step(step1_name)
        wrap_evaluator(E1, root=root1)

    def step1_solution():
        set_step(step1_name)
        wrap_solution(S1, root=root1)

    p_e = Process(target=step1_evaluator)
    p_e.start()
    p_s = Process(target=step1_solution)
    p_s.start()
    p_s.join()
    p_e.join()

    cr1 = read_challenge_results(root1)

    print('cr1: %s' % json.dumps(cr1.to_yaml(), indent=4))

    if cr1.status in ['error', 'failed']:
        return cr1, None

    root2 = tempfile.mkdtemp()
    print('Root2: %s' % root2)

    os.makedirs(os.path.join(root2, CHALLENGE_PREVIOUS_STEPS_DIR))
    l = os.path.join(root2, CHALLENGE_PREVIOUS_STEPS_DIR, step1_name)
    # os.link(root1, l)
    shutil.copytree(root1, l)

    def step2_evaluator():
        set_step(step2_name)
        wrap_evaluator(E2, root=root2)

    def step2_solution():
        set_step(step2_name)
        wrap_solution(S2, root=root2)

    p_e = Process(target=step2_evaluator)
    p_e.start()
    p_s = Process(target=step2_solution)
    p_s.start()
    p_s.join()
    p_e.join()

    cr2 = read_challenge_results(root2)
    print('cr2: %s' % json.dumps(cr2.to_yaml(), indent=4))
    return cr1, cr2


step1_name = 'step1'
step2_name = 'step2'

S1fn = 'S1fn'
E1fn = 'E1fn'


class E1(ChallengeEvaluator):

    def prepare(self, cie):
        assert isinstance(cie, ChallengeInterfaceEvaluator)
        cie.set_challenge_parameters({})
        assert step1_name == cie.get_current_step()
        assert [] == cie.get_completed_steps()

    def score(self, cie):
        assert isinstance(cie, ChallengeInterfaceEvaluator)
        cie.set_score('passed1', 1)

        cie.set_evaluation_file_from_data(E1fn, b'one')


class S1(ChallengeSolution):

    def run(self, cis):
        assert isinstance(cis, ChallengeInterfaceSolution)

        assert step1_name == cis.get_current_step()
        assert [] == cis.get_completed_steps()

        cis.set_solution_output_file_from_data(S1fn, b'two')
        cis.info('hello')
        cis.set_solution_output_dict({})


class E2(ChallengeEvaluator):

    def prepare(self, cie):
        assert isinstance(cie, ChallengeInterfaceEvaluator)

        assert step2_name == cie.get_current_step()
        assert [step1_name] == cie.get_completed_steps()

        cie.info(cie.get_completed_step_evaluation_files(step1_name))

        assert [E1fn] == cie.get_completed_step_evaluation_files(step1_name)

        cie.set_challenge_parameters({})

    def score(self, cie):
        assert isinstance(cie, ChallengeInterfaceEvaluator)
        cie.set_score('passed2', 1)


class S2(ChallengeSolution):

    def run(self, cis):
        assert isinstance(cis, ChallengeInterfaceSolution)

        assert step2_name == cis.get_current_step()
        assert [step1_name] == cis.get_completed_steps()

        cis.info('see: %s' % cis.get_completed_step_solution_files(step1_name))
        assert {S1fn, 'output-solution.yaml'} == set(cis.get_completed_step_solution_files(step1_name))

        cis.set_solution_output_dict({})


@comptest
def test_interaction_two_steps():
    run_interaction_two_steps(step1_name, S1(), E1(), step2_name, S2(), E2())


if __name__ == '__main__':
    run_module_tests()
