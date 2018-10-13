import argparse
import os
import random
import shutil
import subprocess

import docker
import yaml
from dt_shell.remote import make_server_request
from duckietown_challenges import CHALLENGE_PREVIOUS_STEPS_DIR
from duckietown_challenges.challenge import ChallengeDescription
from duckietown_challenges.runner import run_single
from duckietown_challenges.submission_build import read_submission_info, build_image

usage = """




"""


def runner_local_main():
    prog = 'dts challenges evaluate'
    parser = argparse.ArgumentParser(prog=prog, usage=usage)

    group = parser.add_argument_group('Basic')

    group.add_argument('--no-cache', action='store_true', default=False,
                       help="")

    group.add_argument('--no-build', action='store_true', default=False,
                       help="")
    group.add_argument('--output', default='output-local-evaluation')

    group.add_argument('-C', dest='change', default=None)


    parsed = parser.parse_args()

    if parsed.change:
        os.chdir(parsed.change)

    path = os.getcwd()
    subinfo = read_submission_info(path)

    dockerfile = os.path.join(path, 'Dockerfile')
    if not os.path.exists(dockerfile):
        msg = 'I expected to find the file "%s".' % dockerfile
        raise Exception(msg)

    client = docker.from_env()

    no_cache = parsed.no_cache
    no_build = parsed.no_build
    do_pull = False

    result = get_challenge_description(subinfo.challenge_name)
    cd = ChallengeDescription.from_yaml(result['challenge'])

    image = build_image(client, path, dockerfile, no_cache=no_cache, no_build=no_build)

    solution_container = image.id

    steps_ordered = list(sorted(cd.steps))
    for i, challenge_step_name in enumerate(steps_ordered):
        step = cd.steps[challenge_step_name]

        wd_final = os.path.join(parsed.output, challenge_step_name)
        if os.path.exists(wd_final):
            print('Not redoing step %r' % step)
            print('Erase %s if you want to redo it.' % wd_final)
            continue

        wd = wd_final + '.tmp'

        if os.path.exists(wd):
            shutil.rmtree(wd)

        previous = steps_ordered[:i]
        for previous_step in previous:
            pd = os.path.join(wd, CHALLENGE_PREVIOUS_STEPS_DIR)
            if not os.path.exists(pd):
                os.makedirs(pd)

            d = os.path.join(pd, previous_step)
            # p = os.path.realpath(os.path.join(parsed.output, previous_step))
            os.symlink('../../%s' % previous_step, d)

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
            f.write(yaml.dump(cr.to_yaml()))

        os.rename(wd, wd_final)

    print('find your output here: %s' % parsed.output)


def get_challenge_description(challenge_name):
    endpoint = '/challenges/%s/description' % challenge_name
    method = 'GET'
    data = {}
    return make_server_request(None, endpoint, data=data, method=method)


if __name__ == '__main__':
    runner_local_main()
