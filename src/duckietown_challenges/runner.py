#!/usr/bin/env python
import StringIO
import argparse
import getpass
import json
import logging
import mimetypes
import os
import platform
import socket
import sys
import tempfile
import time
import traceback
from collections import OrderedDict

from dt_shell.constants import DTShellConstants
from dt_shell.env_checks import check_executable_exists, InvalidEnvironment, check_docker_environment, \
    get_dockerhub_username
from dt_shell.remote import ConnectionError, make_server_request, DEFAULT_DTSERVER

from . import __version__
from .challenge_results import read_challenge_results, ChallengeResults, ChallengeResultsStatus
from .constants import CHALLENGE_SOLUTION_OUTPUT_DIR, CHALLENGE_RESULTS_DIR, CHALLENGE_DESCRIPTION_DIR, \
    CHALLENGE_EVALUATION_OUTPUT_DIR

logging.basicConfig()
elogger = logging.getLogger('evaluator')
elogger.setLevel(logging.DEBUG)


def get_token_from_shell_config():
    path = os.path.join(os.path.expanduser(DTShellConstants.ROOT), 'config')
    data = open(path).read()
    config = json.loads(data)
    k = DTShellConstants.DT1_TOKEN_CONFIG_KEY
    if k not in config:
        msg = 'Please set a Duckietown Token using the command `dts tok set`.'
        raise Exception(msg)
    else:
        return config[k]


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

    do_pull = not parsed.no_pull

    try:
        docker_username = get_dockerhub_username()
    except Exception:
        msg = 'Skipping push because docker_username is not set.'
        elogger.debug(msg)
        docker_username = None

    if parsed.continuous:

        timeout = 5.0  # seconds
        multiplier = 1.0
        max_multiplier = 10
        while True:
            multiplier = min(multiplier, max_multiplier)
            try:
                go_(None, do_pull, docker_username)
                multiplier = 1.0
            except NothingLeft:
                sys.stderr.write('.')
                # time.sleep(timeout * multiplier)
                # elogger.info('No submissions available to evaluate.')
            except ConnectionError as e:
                elogger.error(e)
                multiplier *= 1.5
            except Exception as e:
                msg = 'Uncaught exception:\n%s' % traceback.format_exc(e)
                elogger.error(msg)
                multiplier *= 1.5

            time.sleep(timeout * multiplier)

    else:
        submissions = parsed.extra

        if not submissions:
            submissions = [None]

        for submission_id in submissions:
            try:
                go_(submission_id, do_pull, docker_username)
            except NothingLeft:
                elogger.info('No submissions available to evaluate.')


class NothingLeft(Exception):
    pass


def get_features():
    import psutil

    features = {}

    machine = platform.machine()
    features['linux'] = sys.platform.startswith('linux')
    features['mac'] = sys.platform.startswith('darwin')
    features['x86_64'] = (machine == 'x86_64')
    features['armv7l'] = (machine == 'armv7l')
    meminfo = psutil.virtual_memory()
    # svmem(total=16717422592, available=5376126976, percent=67.8, used=10359984128, free=1831890944, active=7191916544, inactive=2325667840, buffers=525037568, cached=4000509952, shared=626225152)

    features['ram_total_mb'] = int(meminfo.total / (1024 * 1024.0))
    features['ram_available_mb'] = int(meminfo.available / (1024 * 1024.0))
    features['nprocessors'] = psutil.cpu_count()
    features['processor_frequency_mhz'] = int(psutil.cpu_freq().max)
    f = psutil.cpu_percent(interval=0.2)
    features['processor_free_percent'] = int(100.0 - f)
    features['p1'] = True

    disk = psutil.disk_usage(os.getcwd())

    features['disk_total_mb'] = disk.total / (1024 * 1024)
    features['disk_available_mb'] = disk.free / (1024 * 1024)
    features['picamera'] = False
    features['nduckiebots'] = False
    features['map_3x3'] = False

    print yaml.dump(features)
    return features


import yaml


def go_(submission_id, do_pull, docker_username):
    features = get_features()
    token = get_token_from_shell_config()
    machine_id = socket.gethostname()

    evaluator_version = __version__

    process_id = str(os.getpid())

    res = dtserver_work_submission(token, submission_id, machine_id, process_id, evaluator_version,
                                   features=features)

    if 'job_id' not in res:
        msg = 'Could not find jobs: %s' % res['msg']
        raise NothingLeft(msg)

    elogger.info(res)
    job_id = res['job_id']

    elogger.info('Evaluating job %s' % job_id)
    # submission_id = result['submission_id']
    # parameters = result['parameters']
    # job_id = result['job_id']
    evaluation_container = None

    artifacts_image = size = None
    try:
        wd = tempfile.mkdtemp(prefix='tmp-duckietown-challenge-evaluator-')

        LAST = 'last'
        if os.path.lexists(LAST):
            os.unlink(LAST)
        os.symlink(wd, LAST)

        challenge_name = res['challenge_name']
        solution_container = res['parameters']['hash']
        challenge_parameters = res['challenge_parameters']
        aws_config = res['aws_config']
        bucket_name = aws_config['bucket_name']
        aws_access_key_id = aws_config['aws_access_key_id']
        aws_secret_access_key = aws_config['aws_secret_access_key']
        aws_root_path = aws_config['path']
        import boto3
        s3 = boto3.resource("s3",
                            aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key)

        s = 'initial data'
        data = StringIO.StringIO(s)
        print('trying bucket connection')
        object = s3.Object(bucket_name, os.path.join(aws_root_path, 'initial.txt'))
        object.upload_fileobj(data)
        print('uploaded')
        # evaluation_protocol = challenge_parameters['protocol']
        # assert evaluation_protocol == 'p1'
        if res['protocol'] != 'p1':
            msg = 'invalid protocol %s' % res['protocol']
            elogger.error(msg)
            raise Exception(msg)

        evaluation_container = challenge_parameters['container']

        UID = os.getuid()
        USERNAME = getpass.getuser()

        challenge_solution_output_dir = os.path.join(wd, CHALLENGE_SOLUTION_OUTPUT_DIR)
        challenge_results_dir = os.path.join(wd, CHALLENGE_RESULTS_DIR)
        challenge_description_dir = os.path.join(wd, CHALLENGE_DESCRIPTION_DIR)
        challenge_evaluation_output_dir = os.path.join(wd, CHALLENGE_EVALUATION_OUTPUT_DIR)

        for d in [challenge_solution_output_dir, challenge_results_dir, challenge_description_dir,
                  challenge_evaluation_output_dir]:
            os.makedirs(d)

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

        #         df = os.path.join(wd, 'Dockerfile')
        #         with open(df, 'w') as f:
        #             f.write("""
        # FROM scratch
        # COPY . /jobs/%s
        #
        #             """ % job_id)

        dcfn = os.path.join(wd, 'docker-compose.yaml')

        print(compose)
        with open(dcfn, 'w') as f:
            f.write(compose)

        if do_pull:
            cmd = ['docker-compose', '-f', dcfn, 'pull']
            ret = os.system(" ".join(cmd))
            if ret != 0:
                msg = 'Could not run docker-compose pull.'
                raise Exception(msg)

        cmd = ['docker-compose', '-f', dcfn, 'up']
        ret = os.system(" ".join(cmd))
        if ret != 0:
            msg = 'Could not run docker-compose.'
            raise Exception(msg)

        # os.system('find %s' % wd)
        try:
            cr = read_challenge_results(wd)
        except Exception as e:
            msg = 'Could not read the challenge results:\n%s' % traceback.format_exc(e)
            elogger.error(msg)
            status = ChallengeResultsStatus.ERROR
            cr = ChallengeResults(status, msg, scores={})

        create_index_files(wd, job_id=job_id)
        toupload = OrderedDict()
        for dirpath, dirnames, filenames in os.walk(wd):
            for f in filenames:
                rpath = os.path.join(os.path.relpath(dirpath, wd), f)
                if rpath.startswith('./'):
                    rpath = rpath[2:]
                toupload[rpath] = os.path.join(dirpath, f)

        uploaded = []
        for rpath, realfile in toupload.items():
            object_key = os.path.join(aws_root_path, rpath)
            statinfo = os.stat(realfile)
            size = statinfo.st_size

            print('uploading %.1fMB %s to %s from %s' % (size / (1024 * 1024.0), rpath, object_key, realfile))

            mime_type, _encoding = mimetypes.guess_type(realfile)

            print('guessed %s' % mime_type)
            if mime_type is None:
                if realfile.endswith('.yaml'):
                    mime_type = 'text/yaml'
                else:
                    mime_type = 'binary/octet-stream'

            aws_object = s3.Object(bucket_name, object_key)
            aws_object.upload_file(realfile, ExtraArgs={'ContentType': mime_type})
            uploaded.append(dict(object_key=object_key, bucket_name=bucket_name, size=size,
                                 mime_type=mime_type, rpath=rpath))

        # if docker_username is not None:
        #     import docker
        #     client = docker.from_env()
        #
        #     tag = '%s/jobs:%s' % (docker_username, job_id)
        #     out = client.images.build(path=wd, tag=tag)
        #     for line in out:
        #         print(line)
        #
        #     image = client.images.get(tag)
        #     artifacts_image = '%s@%s' % (tag, image.id)
        #
        #     size = image.attrs['Size']
        #
        #     print(artifacts_image)
        #
        #     elogger.info('Pushing image %s' % tag)
        #     client.images.push(tag)
        # else:
        #     size = artifacts_image = None


    except NothingLeft:
        raise
    except Exception as e:  # XXX
        msg = 'Uncaught exception:\n%s' % traceback.format_exc()
        elogger.error(msg)
        status = ChallengeResultsStatus.ERROR
        cr = ChallengeResults(status, msg, scores={})
        uploaded = []

    stats = cr.get_stats()
    if artifacts_image:
        stats['artifacts'] = dict(size=size, image=artifacts_image)

    dtserver_report_job(token,
                        job_id=job_id,
                        stats=stats,
                        result=cr.get_status(),
                        machine_id=machine_id,
                        process_id=process_id,
                        evaluation_container=evaluation_container,
                        evaluator_version=evaluator_version,
                        uploaded=uploaded)
    #
    # process_id = data['process_id']
    # evaluator_version = data['evaluator_version']
    # evaluation_container = data['evaluation_container']


def dtserver_report_job(token, job_id, result, stats, machine_id,
                        process_id, evaluation_container, evaluator_version, uploaded):
    endpoint = '/take-submission'
    method = 'POST'
    data = {'job_id': job_id,
            'result': result,
            'stats': stats,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluation_container': evaluation_container,
            'evaluator_version': evaluator_version,
            'uploaded': uploaded
            }
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_work_submission(token, submission_id, machine_id, process_id, evaluator_version, features):
    endpoint = '/take-submission'
    method = 'GET'
    data = {'submission_id': submission_id,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluator_version': evaluator_version,
            'features': features}
    return make_server_request(token, endpoint, data=data, method=method)


def create_index_files(wd, job_id):
    for root, dirnames, filenames in os.walk(wd, followlinks=True):
        print(root, dirnames, filenames)
        index = os.path.join(root, 'index.html')
        if not os.path.exists(index):
            with open(index, 'w') as f:
                f.write(create_index(root, dirnames, filenames, job_id))


def create_index(root, dirnames, filenames, job_id):

    s = "<html><head></head><body>\n"

    url = DEFAULT_DTSERVER + '/humans/jobs/%s' % job_id
    s += '<p>These are the output for <a href="%s">Job %s</a>' % (url, job_id)
    s += '<table>'

    for d in dirnames:
        s += '\n<tr><td></td><td><a href="%s">%s/</td></tr>' % (d, d)

    for f in filenames:
        size = os.stat(os.path.join(root, f)).st_size
        s += '\n<tr><td>%.3f MB</td><td><a href="%s">%s</td></tr>' % (size / (1024 * 1024.0), f, f)

    s += '\n</table>'
    s += '\n</body></head>'
    return s
