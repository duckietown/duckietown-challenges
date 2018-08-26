#!/usr/bin/env python
import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time

from dt_shell.constants import DTShellConstants
from dt_shell.env_checks import check_executable_exists, InvalidEnvironment, check_docker_environment
from dt_shell.remote import dtserver_work_submission, dtserver_report_job

logging.basicConfig()
elogger = logging.getLogger('evaluator')
elogger.setLevel(logging.DEBUG)


def get_token_from_shell_config():
    path = os.path.join(os.path.expanduser(DTShellConstants.ROOT), 'config')
    data = open(path).read()
    config = json.loads(data)
    return config[DTShellConstants.DT1_TOKEN_CONFIG_KEY]


from . import __version__


def dt_challenges_evaluator():
    elogger.info("dt-challenges-evaluator %s" % __version__)

    check_docker_environment()
    try:
        check_executable_exists('docker-compose')
    except InvalidEnvironment:
        msg = 'Could not find docker-compose. Please install it.'
        msg += '\n\nSee: https://docs.docker.com/compose/install/#install-compose'
        raise InvalidEnvironment(msg)

    parser = argparse.ArgumentParser()
    parser.add_argument("--continuous", action="store_true", default=False)
    parser.add_argument("extra", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    if parsed.continuous:

        while True:
            try:
                go_(None)
            except NothingLeft:
                sys.stderr.write('.')
                # elogger.info('No submissions available to evaluate.')
                time.sleep(5)

    else:
        submissions = parsed.extra

        if not submissions:
            submissions = [None]

        for submission_id in submissions:

            try:
                go_(submission_id)
            except NothingLeft:
                elogger.info('No submissions available to evaluate.')


class NothingLeft(Exception):
    pass


def go_(submission_id):
    token = get_token_from_shell_config()
    res = dtserver_work_submission(token, submission_id)

    if 'job_id' not in res:
        msg = 'Could not find jobs: %s' % res['msg']
        raise NothingLeft(msg)
    job_id = res['job_id']

    elogger.info('Evaluating job %s' % job_id)
    # submission_id = result['submission_id']
    # parameters = result['parameters']
    # job_id = result['job_id']

    wd = tempfile.mkdtemp(prefix='tmp-duckietown-challenge-evaluator-')
    elogger.debug('Using temporary dir %s' % wd)
    # pwd = os.getcwd()
    output_solution = os.path.join(wd, 'output-solution')
    output_evaluation = os.path.join(wd, 'output-evaluation')

    # for d in [output_evaluation, output_solution]:
    #     if os.path.exists(d):
    #         shutil.rmtree(d)
    #         os.makedirs(d)

    challenge_name = res['challenge_name']
    solution_container = res['parameters']['hash']
    evaluation_protocol = res['challenge_parameters']['protocol']
    assert evaluation_protocol == 'p1'

    evaluation_container = res['challenge_parameters']['container']
    # username = getpass.getuser()
    username = os.getuid()
    compose = """
    
version: '3'

services:
  solution:
    image: {solution_container}
    
    volumes:
    - assets:/challenges/{challenge_name}/solution
    - {output_solution}:/challenges/{challenge_name}/output-solution
  evaluator:
    image: {evaluation_container} 
    
    volumes:
    - assets:/challenges/{challenge_name}/solution
    - {output_evaluation}:/challenges/{challenge_name}/output-evaluation
    
volumes:
  assets:
""".format(challenge_name=challenge_name,
           evaluation_container=evaluation_container,
           solution_container=solution_container,
           output_evaluation=output_evaluation,
           output_solution=output_solution,
           username=username)

    with open('docker-compose.yaml', 'w') as f:
        f.write(compose)

    cmd = ['docker-compose', 'pull']
    ret = os.system(" ".join(cmd))
    if ret != 0:
        msg = 'Could not run docker-compose.'
        raise Exception(msg)
    cmd = ['docker-compose', 'up']
    ret = os.system(" ".join(cmd))
    if ret != 0:
        msg = 'Could not run docker-compose.'
        raise Exception(msg)

    output_f = os.path.join(output_evaluation, 'output.json')
    output = json.loads(open(output_f).read())
    print(json.dumps(output, indent=4))
    stats = output
    result = output.pop('result')
    dtserver_report_job(token, job_id=job_id, stats=stats, result=result)
