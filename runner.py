#!/usr/bin/env python

import json
import os
import shutil
import sys

import yaml
from dt_shell.constants import DTShellConstants
from dt_shell.remote import dtserver_work_submission, dtserver_report_job


def get_token_from_shell_config():
    path = os.path.join(os.path.expanduser(DTShellConstants.ROOT), 'config')
    data = open(path).read()
    config = json.loads(data)
    return config[DTShellConstants.DT1_TOKEN_CONFIG_KEY]


def go():
    submissions = map(int, sys.argv[1:])
    if not submissions:
        submissions = [None]

    for submission_id in submissions:
        go_(submission_id)


def go_(submission_id):
    token = get_token_from_shell_config()
    res = dtserver_work_submission(token, submission_id)

    if not 'job_id' in res:
        msg = 'Could not find jobs: %s' % res['msg']
        print(msg)
        return
    #
    # submission_id = result['submission_id']
    # parameters = result['parameters']
    # job_id = result['job_id']

    pwd = os.getcwd()
    output_solution = os.path.join(pwd, 'output-solution')
    output_evaluation = os.path.join(pwd, 'output-evaluation')

    for d in [output_evaluation, output_solution]:
        if os.path.exists(d):
            shutil.rmtree(d)
            os.makedirs(d)

    job_id = res['job_id']

    challenge_name = res['challenge_name']
    solution_container = res['parameters']['hash']
    evaluation_protocol = res['challenge_parameters']['protocol']
    assert evaluation_protocol == 'p1'

    evaluation_container = res['challenge_parameters']['container']

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
           output_solution=output_solution)

    with open('docker-compose.yaml', 'w') as f:
        f.write(compose)

    cmd = ['docker-compose', 'pull']
    os.system(" ".join(cmd))
    cmd = ['docker-compose', 'up']
    os.system(" ".join(cmd))

    output_f = os.path.join(output_evaluation, 'output.json')
    output = json.loads(open(output_f).read())
    print(json.dumps(output, indent=4))
    stats = output
    result = output.pop('result')
    dtserver_report_job(token, job_id=job_id, stats=stats, result=result)


if __name__ == '__main__':
    go()
