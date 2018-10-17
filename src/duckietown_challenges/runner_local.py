import argparse
import os
import random
import shutil
import subprocess
import sys
import traceback

import docker
import termcolor
import yaml

from dt_shell.remote import make_server_request
from duckietown_challenges import CHALLENGE_PREVIOUS_STEPS_DIR, ChallengeResults
from .challenge import ChallengeDescription
from .runner import run_single, get_token_from_shell_config
from .submission_build import read_submission_info, build_image
from .utils import indent

usage = """




"""
import logging

logger = logging.getLogger('runner-local')
logger.setLevel(logging.DEBUG)


def runner_local_main():
    try:
        runner_local_main_()
    except BaseException as e:
        logger.error(traceback.format_exc(e))
        sys.exit(2)


def runner_local_main_():
    from .col_logging import setup_logging_color
    setup_logging_color()
    prog = 'dts challenges evaluate'
    parser = argparse.ArgumentParser(prog=prog, usage=usage)

    group = parser.add_argument_group('Basic')

    group.add_argument('--no-cache', action='store_true', default=False,
                       help="")

    group.add_argument('--no-build', action='store_true', default=False,
                       help="")
    group.add_argument('--output', default='output-local-evaluation')

    group.add_argument('--challenge', default=None, help='override challenge')

    group.add_argument('-C', dest='change', default=None)

    parsed = parser.parse_args()

    logger.debug('Running in directory %s' % os.getcwd())

    if parsed.change:
        os.chdir(parsed.change)
        logger.debug('Changing to directory %s' % os.getcwd())

    token = get_token_from_shell_config()
    path = '.'
    # path = os.getcwd()

    # if not os.path.exists(path):
    #     msg = 'The current path does not exist: %s' % path
    #     msg += '\nWow, this is a bug.'
    #     raise Exception(msg)

    subinfo = read_submission_info(path)

    dockerfile = os.path.join(path, 'Dockerfile')
    if not os.path.exists(dockerfile):
        msg = 'I expected to find the file "%s".' % dockerfile
        raise Exception(msg)

    client = docker.from_env()

    no_cache = parsed.no_cache
    no_build = parsed.no_build
    do_pull = False

    if parsed.challenge is not None:
        subinfo.challenge_name = parsed.challenge

    result = get_challenge_description(token, subinfo.challenge_name)
    cd = ChallengeDescription.from_yaml(result['challenge'])

    image = build_image(client, path, dockerfile, no_cache=no_cache, no_build=no_build)

    solution_container = image.id
    SUCCESS = 'success'
    steps_ordered = list(sorted(cd.steps))
    logger.info('steps: %s' % steps_ordered)
    for i, challenge_step_name in enumerate(steps_ordered):
        logger.info('Now considering step "%s"' % challenge_step_name)
        step = cd.steps[challenge_step_name]
        evaluation_parameters_str = yaml.safe_dump(
                step.evaluation_parameters.as_dict()) + '\ns: %s' % solution_container

        wd_final = os.path.join(parsed.output, challenge_step_name)
        params = os.path.join(wd_final, 'parameters.json')
        if os.path.exists(wd_final) and os.path.exists(params):
            if open(params).read() == evaluation_parameters_str:
                cr_yaml = open(os.path.join(wd_final, 'results.yaml'))
                cr = ChallengeResults.from_yaml(yaml.load(cr_yaml))
                if cr.status == SUCCESS:
                    logger.info('Not redoing step "%s" because it is already completed.' % challenge_step_name)
                    logger.info('If you want to re-do it, erase the directory %s.' % wd_final)
                    continue
                else:
                    logger.error('Breaking because step "%s" had result "%s".' % (challenge_step_name, cr.status))
                    break
            else:
                logger.info('I will redo the step because the parameters changed.')
                if os.path.exists(wd_final):
                    shutil.rmtree(wd_final)

        wd = wd_final + '.tmp'

        if os.path.exists(wd):
            shutil.rmtree(wd)
        params_tmp = os.path.join(wd, 'parameters.json')
        if not os.path.exists(wd):
            os.makedirs(wd)
        with open(params_tmp, 'w') as f:
            f.write(evaluation_parameters_str)

        previous = steps_ordered[:i]
        for previous_step in previous:
            pd = os.path.join(wd, CHALLENGE_PREVIOUS_STEPS_DIR)
            if not os.path.exists(pd):
                os.makedirs(pd)

            d = os.path.join(pd, previous_step)
            # os.symlink('../../%s' % previous_step, d)
            p = os.path.join(parsed.output, previous_step)
            shutil.copytree(p, d)

            mk = os.path.join(d, 'docker-compose.yaml')
            if not os.path.exists(mk):
                subprocess.check_call(['find', wd])
                raise Exception()
        aws_config = None
        steps2artefacts = {}
        evaluation_parameters = step.evaluation_parameters

        project = 'project%s' % random.randint(1, 100)
        cr = run_single(wd, aws_config, steps2artefacts, evaluation_parameters, solution_container=solution_container,
                        challenge_name=subinfo.challenge_name,
                        challenge_step_name=challenge_step_name,
                        project=project,
                        do_pull=do_pull)
        fn = os.path.join(wd, 'results.yaml')
        with open(fn, 'w') as f:
            res = yaml.dump(cr.to_yaml())
            f.write(res)

        s = ""
        s += '\nStatus: %s' % cr.status
        s += '\nScores:\n\n%s' % yaml.safe_dump(cr.scores, default_flow_style=False)
        s += '\n\n%s' % cr.msg
        logger.info(indent(s, dark('step %s : ' % challenge_step_name)))

        os.rename(wd, wd_final)

        if cr.status != SUCCESS:
            logger.error('Breaking because step "%s" has result %s.' % (challenge_step_name, cr.status))
            break

    print('find your output here: %s' % parsed.output)


def dark(x):
    return termcolor.colored(x, attrs=['dark'])


def get_challenge_description(token, challenge_name):
    endpoint = '/challenges/%s/description' % challenge_name
    method = 'GET'
    data = {}
    return make_server_request(token, endpoint, data=data, method=method)


if __name__ == '__main__':
    runner_local_main()
