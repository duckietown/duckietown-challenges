#!/usr/bin/env python
import argparse
import json
import logging
import os
import socket
import sys
import tempfile
import time
import traceback

import yaml

from dt_shell.constants import DTShellConstants
from dt_shell.env_checks import check_executable_exists, InvalidEnvironment, check_docker_environment
from dt_shell.remote import dtserver_work_submission, dtserver_report_job, ConnectionError
from . import __version__, CONFIG_LOCATION, CHALLENGE_SOLUTION_OUTPUT, CHALLENGE_EVALUATION_OUTPUT, CHALLENGE_SOLUTION, \
    CHALLENGE_EVALUATION

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
        elogger.debug('Using temporary dir %s' % wd)
        output_solution = os.path.join(wd, 'output-solution')
        output_evaluation = os.path.join(wd, 'output-evaluation')

        challenge_name = res['challenge_name']
        solution_container = res['parameters']['hash']
        evaluation_protocol = res['challenge_parameters']['protocol']
        assert evaluation_protocol == 'p1'

        config_dir = os.path.join(wd, 'config')
        os.makedirs(config_dir)

        evaluation_container = res['challenge_parameters']['container']
        # username = getpass.getuser()
        username = os.getuid()

        config = {
            'input_dir': None,
            'previous_step_dir': None,
            'output_dir': CHALLENGE_SOLUTION_OUTPUT,
            'temp_dir': None,
        }
        fn = os.path.join(config_dir, os.path.basename(CONFIG_LOCATION))
        with open(fn, 'w') as f:
            f.write(yaml.dump(config))


        compose = """
        
    version: '3'
    
    services:
      solution:
        image: {solution_container}
        
        volumes:
        - challenge_solution:{CHALLENGE_SOLUTION}
        - {output_solution}:{CHALLENGE_SOLUTION_OUTPUT}
        
      evaluator:
        image: {evaluation_container} 
        
        volumes:
        - challenge_solution:{CHALLENGE_SOLUTION}
        - {output_evaluation}:{CHALLENGE_EVALUATION_OUTPUT}

    volumes:
      challenge_solution:
      
      
    """.format(challenge_name=challenge_name,
               evaluation_container=evaluation_container,
               solution_container=solution_container,
               output_evaluation=output_evaluation,
               output_solution=output_solution,
               username=username,
               CHALLENGE_SOLUTION_OUTPUT=CHALLENGE_SOLUTION_OUTPUT,
               CHALLENGE_EVALUATION_OUTPUT=CHALLENGE_EVALUATION_OUTPUT,
               CHALLENGE_SOLUTION=CHALLENGE_SOLUTION,
               CHALLENGE_EVALUATION=CHALLENGE_EVALUATION)

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

        output_f = os.path.join(output_evaluation, 'output.json')
        output = json.loads(open(output_f).read())
        elogger.debug("output from evaluator: %s" % json.dumps(output, indent=4))
        stats = output
        result = output.pop('result')
        dtserver_report_job(token, job_id=job_id, stats=stats, result=result,
                            machine_id=machine_id)
    except NothingLeft:
        raise
    except Exception as e:  # XXX
        elogger.error(e)
        result = 'failed'
        stats = {'exception': traceback.format_exc(e)}
        dtserver_report_job(token, job_id, result=result, stats=stats,
                            machine_id=machine_id)
