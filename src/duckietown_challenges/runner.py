#!/usr/bin/env python
import argparse
import getpass
import json
import logging
import os
import socket
import sys
import tempfile
import time
import traceback

from dt_shell.constants import DTShellConstants
from dt_shell.env_checks import check_executable_exists, InvalidEnvironment, check_docker_environment
from dt_shell.remote import dtserver_work_submission, dtserver_report_job, ConnectionError
from . import __version__
from .challenge_results import read_challenge_results
from .constants import CHALLENGE_SOLUTION_OUTPUT_DIR, CHALLENGE_RESULTS_DIR, CHALLENGE_DESCRIPTION_DIR, \
    CHALLENGE_EVALUATION_OUTPUT_DIR

logging.basicConfig()
elogger = logging.getLogger('evaluator')
elogger.setLevel(logging.DEBUG)


def get_token_from_shell_config():
    path = os.path.join(os.path.expanduser(DTShellConstants.ROOT), 'config')
    data = open(path).read()
    config = json.loads(data)
    return config[DTShellConstants.DT1_TOKEN_CONFIG_KEY]


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
    parser.add_argument("--no-pull", dest='no_pull', action="store_true", default=False)
    parser.add_argument("extra", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()
    print parsed

    do_pull = not parsed.no_pull

    if parsed.continuous:

        timeout = 5.0  # seconds
        multiplier = 1.0
        max_multiplier = 10
        while True:
            multiplier = min(multiplier, max_multiplier)
            try:
                go_(None, do_pull)
                multiplier = 1.0
            except NothingLeft:
                sys.stderr.write('.')
                time.sleep(timeout * multiplier)
                # elogger.info('No submissions available to evaluate.')
            except ConnectionError as e:
                elogger.error(e)
                multiplier *= 1.5
            except Exception as e:
                msg = 'Weird exception: %s' % e
                elogger.error(msg)
                multiplier *= 1.5


    else:
        submissions = parsed.extra

        if not submissions:
            submissions = [None]

        for submission_id in submissions:
            try:
                go_(submission_id, do_pull)
            except NothingLeft:
                elogger.info('No submissions available to evaluate.')


class NothingLeft(Exception):
    pass


def go_(submission_id, do_pull):
    token = get_token_from_shell_config()
    machine_id = socket.gethostname()
    res = dtserver_work_submission(token, submission_id, machine_id)

    if 'job_id' not in res:
        msg = 'Could not find jobs: %s' % res['msg']
        raise NothingLeft(msg)
    job_id = res['job_id']

    elogger.info('Evaluating job %s' % job_id)
    # submission_id = result['submission_id']
    # parameters = result['parameters']
    # job_id = result['job_id']

    try:
        wd = tempfile.mkdtemp(prefix='tmp-duckietown-challenge-evaluator-')

        LAST = 'last'
        if os.path.lexists(LAST):
            os.unlink(LAST)
        os.symlink(wd, LAST)

        challenge_name = res['challenge_name']
        solution_container = res['parameters']['hash']
        challenge_parameters = res['challenge_parameters']
        print(challenge_parameters)
        evaluation_protocol = challenge_parameters['protocol']
        assert evaluation_protocol == 'p1'

        evaluation_container = challenge_parameters['container']

        UID = os.getuid()
        USERNAME = getpass.getuser()

        challenge_solution_output_dir = os.path.join(wd, CHALLENGE_SOLUTION_OUTPUT_DIR)
        challenge_results_dir = os.path.join(wd, CHALLENGE_RESULTS_DIR)
        challenge_description_dir = os.path.join(wd, CHALLENGE_DESCRIPTION_DIR)
        challenge_evaluation_output_dir = os.path.join(wd, CHALLENGE_EVALUATION_OUTPUT_DIR)

        compose = """
        
    version: '3'
    services:
      solution:
      
        image: {solution_container}
        environment:
            username: {USERNAME}
            uid: {UID}
        
        volumes:
        - {challenge_solution_output_dir}:/{CHALLENGE_SOLUTION_OUTPUT_DIR}
        - {challenge_results_dir}:/{CHALLENGE_RESULTS_DIR}
        - {challenge_description_dir}:/{CHALLENGE_DESCRIPTION_DIR}
        - {challenge_evaluation_output_dir}:/{CHALLENGE_EVALUATION_OUTPUT_DIR}
        
      evaluator:
        image: {evaluation_container} 
        environment:
            username: {USERNAME}
            uid: {UID}
        
        volumes:
        - {challenge_solution_output_dir}:/{CHALLENGE_SOLUTION_OUTPUT_DIR}
        - {challenge_results_dir}:/{CHALLENGE_RESULTS_DIR}
        - {challenge_description_dir}:/{CHALLENGE_DESCRIPTION_DIR}
        - {challenge_evaluation_output_dir}:/{CHALLENGE_EVALUATION_OUTPUT_DIR}
    # volumes:
    #   CHALLENGE_SOLUTION_OUTPUT_DIR:
    #   CHALLENGE_EVALUATION_OUTPUT_DIR:
    #   CHALLENGE_DESCRIPTION_DIR:
    #   CHALLENGE_RESULTS_DIR:
    #   
    #   
    """.format(challenge_name=challenge_name,
               evaluation_container=evaluation_container,
               solution_container=solution_container,
               USERNAME=USERNAME,
               UID=UID,
               challenge_solution_output_dir=challenge_solution_output_dir,
               CHALLENGE_SOLUTION_OUTPUT_DIR=CHALLENGE_SOLUTION_OUTPUT_DIR,
               challenge_results_dir=challenge_results_dir,
               CHALLENGE_RESULTS_DIR=CHALLENGE_RESULTS_DIR,
               challenge_description_dir=challenge_description_dir,
               CHALLENGE_DESCRIPTION_DIR=CHALLENGE_DESCRIPTION_DIR,
               challenge_evaluation_output_dir=challenge_evaluation_output_dir,
               CHALLENGE_EVALUATION_OUTPUT_DIR=CHALLENGE_EVALUATION_OUTPUT_DIR)

        print(compose)
        with open('docker-compose.yaml', 'w') as f:
            f.write(compose)

        if do_pull:
            cmd = ['docker-compose', 'pull']
            ret = os.system(" ".join(cmd))
            if ret != 0:
                msg = 'Could not run docker-compose pull.'
                raise Exception(msg)

        cmd = ['docker-compose', 'up']
        ret = os.system(" ".join(cmd))
        if ret != 0:
            msg = 'Could not run docker-compose.'
            raise Exception(msg)

        cr = read_challenge_results(wd)

        dtserver_report_job(token, job_id=job_id, stats=cr.get_stats(), result=cr.get_result(),
                            machine_id=machine_id)
    except NothingLeft:
        raise
    except Exception as e:  # XXX
        elogger.error(e)
        result = 'failed'
        stats = {'exception': traceback.format_exc(e)}
        dtserver_report_job(token, job_id, result=result, stats=stats,
                            machine_id=machine_id)
