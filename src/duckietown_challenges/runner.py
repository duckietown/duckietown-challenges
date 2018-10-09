#!/usr/bin/env python
import StringIO
import argparse
import copy
import getpass
import json
import logging
import mimetypes
import os
import platform
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from collections import OrderedDict

import yaml

from dt_shell.constants import DTShellConstants
from dt_shell.env_checks import check_executable_exists, InvalidEnvironment, check_docker_environment
from dt_shell.remote import ConnectionError, make_server_request, DEFAULT_DTSERVER
from . import __version__
from .challenge import EvaluationParameters, SUBMISSION_CONTAINER_TAG
from .challenge_results import read_challenge_results, ChallengeResults, ChallengeResultsStatus
from .constants import CHALLENGE_SOLUTION_OUTPUT_DIR, CHALLENGE_RESULTS_DIR, CHALLENGE_DESCRIPTION_DIR, \
    CHALLENGE_EVALUATION_OUTPUT_DIR, ENV_CHALLENGE_NAME, ENV_CHALLENGE_STEP_NAME, CHALLENGE_PREVIOUS_STEPS_DIR
from .utils import safe_yaml_dump, friendly_size

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
    from .col_logging import  setup_logging
    setup_logging()
    elogger.info("dt-challenges-evaluator (DTC %s)" % __version__)
    elogger.info('called with:\n%s' % sys.argv)
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
    parser.add_argument("--no-upload", dest='no_upload', action="store_true", default=False)
    parser.add_argument("--no-delete", dest='no_delete', action="store_true", default=False)
    parser.add_argument("--machine-id", default=None, help='Machine name')
    parser.add_argument("--name", default=None, help='Evaluator name')
    parser.add_argument("--submission", default=None, help='evaluate this particular submission')
    parser.add_argument("--reset", dest='reset', action="store_true", default=False,
                        help='Reset submission')
    parser.add_argument("--features", default='{}')
    parsed = parser.parse_args()

    try:
        more_features = yaml.load(parsed.features)
    except BaseException as e:
        msg = 'Could not evaluate your YAML string %r:\n%s' % (parsed.features, e)
        raise Exception(msg)

    if not isinstance(more_features, dict):
        msg = 'I expected that the features are a dict; obtained %s: %r' % (type(more_features).__name__, more_features)
        raise Exception(msg)

    do_pull = not parsed.no_pull
    do_upload = not parsed.no_upload
    delete = not parsed.no_delete
    reset = parsed.reset
    evaluator_name = parsed.name or 'p-%s' % os.getpid()
    machine_id = parsed.machine_id or socket.gethostname()

    args = dict(do_upload=do_upload, do_pull=do_pull, more_features=more_features,
                delete=delete, evaluator_name=evaluator_name, machine_id=machine_id)
    if parsed.continuous:

        timeout = 5.0  # seconds
        multiplier = 1.0
        max_multiplier = 10
        while True:
            multiplier = min(multiplier, max_multiplier)
            try:
                go_(None, reset=False, **args)
                multiplier = 1.0
            except NothingLeft:
                sys.stderr.write('.')
                # time.sleep(timeout * multiplier)
                # elogger.info('No submissions available to evaluate.')
            except ConnectionError as e:
                elogger.error(e)
                multiplier *= 1.5
            except BaseException as e:
                msg = 'Uncaught exception:\n%s' % traceback.format_exc(e)
                elogger.error(msg)
                multiplier *= 1.5

            time.sleep(timeout * multiplier)

    else:
        if parsed.submission:
            submissions = [parsed.submission]
        else:
            submissions = [None]

        for submission_id in submissions:
            try:
                go_(submission_id, reset=reset, **args)
            except NothingLeft as e:
                if submission_id is None:
                    msg = 'No submissions available to evaluate.'
                else:
                    msg = 'Could not evaluate submission %s.' % submission_id

                msg += '\n' + str(e)
                elogger.error(msg)


class NothingLeft(Exception):
    pass


def get_features(more_features):
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
    cpu_freq = psutil.cpu_freq()
    if cpu_freq is not None:
        # None on Docker
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

    features['gpu'] = os.path.exists('/proc/driver/nvidia/version')

    for k, v in more_features.items():
        if k in features:
            msg = 'Using %r = %r instead of %r' % (k, more_features[k], features[k])
            elogger.info(msg)
        features[k] = v

    # elogger.debug(json.dumps(features, indent=4))

    return features


class DockerComposeFail(Exception):
    pass


def go_(submission_id, do_pull, more_features, do_upload, delete, reset, evaluator_name, machine_id):
    features = get_features(more_features)
    token = get_token_from_shell_config()
    evaluator_version = __version__
    process_id = evaluator_name

    res = dtserver_work_submission(token, submission_id, machine_id, process_id, evaluator_version,
                                   features=features, reset=reset)

    if 'job_id' not in res:
        msg = 'Could not find jobs: %s' % res['msg']
        raise NothingLeft(msg)
    job_id = res['job_id']

    if res['protocol'] != 'p1':
        msg = 'invalid protocol %s' % res['protocol']
        elogger.error(msg)
        raise Exception(msg)

    try:
        elogger.info(safe_yaml_dump(res))

        elogger.info('Evaluating job %s' % job_id)

        aws_config = res['aws_config']
        if aws_config and do_upload:
            try_s3(aws_config)

            # evaluation_protocol = challenge_parameters['protocol']
        # assert evaluation_protocol == 'p1'

        wd = tempfile.mkdtemp(prefix='tmp-duckietown-challenge-evaluator-')
        # you get this from the server
        steps2artefacts = res['steps2artefacts']
        solution_container = res['parameters']['hash']

        challenge_name = res['challenge_name']
        challenge_step_name = res['step_name']
        challenge_parameters_ = EvaluationParameters.from_yaml(res['challenge_parameters'])

        prepare_dir(wd, aws_config, steps2artefacts)

        config = get_config(challenge_parameters_, solution_container, challenge_name, challenge_step_name)
        config_yaml = yaml.safe_dump(config, encoding='utf-8', indent=4, allow_unicode=True)
        elogger.debug('YAML:\n' + config_yaml)

        dcfn = os.path.join(wd, 'docker-compose.yaml')

        # elogger.info('Compose file: \n%s ' % compose)
        with open(dcfn, 'w') as f:
            f.write(config_yaml)

        project = 'job%s-%s' % (job_id, random.randint(1, 10000))

        cr = run(wd, project, do_pull)

        write_logs(wd, project, services=config['services'])

        if do_upload:
            # create_index_files(wd, job_id=job_id)
            uploaded = upload_files(wd, aws_config)
        else:
            uploaded = []

        if delete:
            cmd = ['down']
            run_docker(wd, project, cmd)

            shutil.rmtree(wd)
    except BaseException as e:  # XXX
        msg = 'Uncaught exception:\n%s' % traceback.format_exc(e)
        elogger.error(msg)
        status = ChallengeResultsStatus.ERROR
        cr = ChallengeResults(status, msg, scores={})
        uploaded = []

    msg = 'This is what is being reported.\n\nstatus = %s\n\n%s' % (cr.get_status(), cr.msg)
    if cr.get_status() != ChallengeResultsStatus.SUCCESS:
        elogger.error(msg)
    else:
        elogger.info(msg)

    stats = cr.get_stats()
    # REST call to the duckietown chalenges server
    dtserver_report_job(token,
                        job_id=job_id,
                        stats=stats,
                        result=cr.get_status(),
                        machine_id=machine_id,
                        process_id=process_id,
                        evaluator_version=evaluator_version,
                        uploaded=uploaded)


def run(wd, project, do_pull):
    import docker
    client =docker.from_env()
    try:
        if do_pull:
            elogger.info('pulling containers')
            cmd = ['pull']
            run_docker(wd, project, cmd)

        pruned = client.networks.prune()
        elogger.debug('pruned: %s' % pruned)

        # elogger.info('Creating containers')
        # cmd = ['create', '--force-recreate']
        # run_docker(wd, project, cmd)

        elogger.info('Running containers')
        cmd = ['up',
               # '--remove-orphans',
               # '--abort-on-container-exit'
               ]
        run_docker(wd, project, cmd)

        cr = read_challenge_results(wd)

    except BaseException as e:  # XXX
        msg = 'Uncaught exception while running Docker Compose:\n%s' % traceback.format_exc(e)
        elogger.error(msg)
        status = ChallengeResultsStatus.ERROR
        cr = ChallengeResults(status, msg, scores={})

    return cr


def prepare_dir(wd, aws_config, steps2artefacts):
    # output for the sub
    challenge_solution_output_dir = os.path.join(wd, CHALLENGE_SOLUTION_OUTPUT_DIR)
    # the yaml with the scores
    challenge_results_dir = os.path.join(wd, CHALLENGE_RESULTS_DIR)
    # the results of the "preparation" step
    challenge_description_dir = os.path.join(wd, CHALLENGE_DESCRIPTION_DIR)
    challenge_evaluation_output_dir = os.path.join(wd, CHALLENGE_EVALUATION_OUTPUT_DIR)
    previous_steps_dir = os.path.join(wd, CHALLENGE_PREVIOUS_STEPS_DIR)

    for d in [challenge_solution_output_dir, challenge_results_dir, challenge_description_dir,
              challenge_evaluation_output_dir, previous_steps_dir]:
        os.makedirs(d)

    download_artefacts(aws_config, steps2artefacts, previous_steps_dir)


def get_config(challenge_parameters_, solution_container, challenge_name, challenge_step_name):
    config = challenge_parameters_.as_dict()

    # Adding the submission container
    for service in config['services'].values():
        if service['image'] == SUBMISSION_CONTAINER_TAG:
            service['image'] = solution_container

        image_digest = service.pop('image_digest', None)
        # This is not needed, because the tag is sufficient as it is generated anew.
        # We should perhaps check that we have the right image tag
        #
        # if image_digest is not None:
        #     service['image'] += '@' + image_digest
    # else:
    #     msg = 'Cannot find the tag %s' % SUBMISSION_CONTAINER_TAG
    #     elogger.warning(msg)
    #     # raise Exception(msg)

    # adding extra environment variables:
    UID = os.getuid()
    USERNAME = getpass.getuser()
    extra_environment = dict(username=USERNAME, uid=UID)
    extra_environment[ENV_CHALLENGE_NAME] = challenge_name
    extra_environment[ENV_CHALLENGE_STEP_NAME] = challenge_step_name

    for service in config['services'].values():
        service['environment'].update(extra_environment)

    # add volumes

    volumes = [
        './' + CHALLENGE_SOLUTION_OUTPUT_DIR + ':' + '/' + CHALLENGE_SOLUTION_OUTPUT_DIR,
        './' + CHALLENGE_RESULTS_DIR + ':' + '/' + CHALLENGE_RESULTS_DIR,
        './' + CHALLENGE_DESCRIPTION_DIR + ':' + '/' + CHALLENGE_DESCRIPTION_DIR,
        './' + CHALLENGE_EVALUATION_OUTPUT_DIR + ':' + '/' + CHALLENGE_EVALUATION_OUTPUT_DIR,
        './' + CHALLENGE_PREVIOUS_STEPS_DIR + ':' + '/' + CHALLENGE_PREVIOUS_STEPS_DIR,
    ]

    for service in config['services'].values():
        assert 'volumes' not in service
        service['volumes'] = copy.deepcopy(volumes)

    elogger.info('Now:\n%s' % safe_yaml_dump(config))

    NETWORK_NAME = 'evaluation'
    networks_evaluator = dict(evaluation=dict(aliases=[NETWORK_NAME]))
    for service in config['services'].values():
        service['networks'] = copy.deepcopy(networks_evaluator)
    config['networks'] = dict(evaluation=None)
    return config


def write_logs(wd, project, services):
    for service in services:
        cmd = ['ps', '-q', service]

        try:
            o = run_docker(wd, project, cmd, get_output=True)
            container_id = o.strip()  # \n at the end
        except DockerComposeFail:
            continue

        elogger.info(container_id)
        import docker
        client = docker.from_env()
        logs = logs_for_container(client, container_id)

        fn = os.path.join(wd, 'log-%s.txt' % service)
        with open(fn, 'w') as f:
            f.write(logs)

        from ansi2html import Ansi2HTMLConverter
        conv = Ansi2HTMLConverter()
        html = conv.convert(logs)
        fn = os.path.join(wd, 'log-%s.html' % service)
        with open(fn, 'w') as f:
            f.write(html)


def run_docker(cwd, project, cmd0, get_output=False):
    cmd0 = ['docker-compose', '-p', project] + cmd0
    elogger.info('Running:\n\t%s' % " ".join(cmd0) + '\n\n in %s' % cwd)

    try:
        if get_output:
            return subprocess.check_output(cmd0, cwd=cwd, stderr=sys.stderr)
        else:
            subprocess.call(cmd0, cwd=cwd, stdout=sys.stdout, stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        msg = 'Could not run %s: %s' % (cmd0, e)
        msg += 'Output: %s' % e.output
        raise DockerComposeFail(msg)


def upload_files(wd, aws_config):
    toupload = get_files_to_upload(wd)

    if not aws_config:
        msg = 'Not uploading artefacts because AWS config not passed.'
        elogger.info(msg)
        uploaded = []
    else:
        uploaded = upload(aws_config, toupload)

    return uploaded


def download_artefacts(aws_config, steps2artefacts, wd):
    for step_name, artefacts in steps2artefacts.items():
        step_dir = os.path.join(wd, step_name)
        os.makedirs(step_dir)
        for rpath, data in artefacts.items():
            fn = os.path.join(step_dir, rpath)
            dn = os.path.dirname(fn)
            if not os.path.exists(dn):
                os.makedirs(dn)
            bucket_name = data['bucket_name']
            object_key = data['object_key']
            sha256hex = data['sha256hex']
            size = data['size']

            try:
                get_file_from_cache(fn, sha256hex)
                elogger.info('cache   %7s   %s' % (friendly_size(size), rpath))
            except KeyError:
                elogger.info('AWS     %7s   %s' % (friendly_size(size), rpath))
                get_object(aws_config, bucket_name, object_key, fn)
                copy_to_cache(fn, sha256hex)
            size_now = os.stat(fn).st_size
            if size_now != size:
                msg = 'Corrupt cache or download for %s at %s.' % (data, fn)
                raise ValueError(msg)


cache_dir = '/tmp/duckietown/DT18/evaluator/cache'
cache_dir_by_value = os.path.join(cache_dir, 'by-value', 'sha256hex')


def try_s3(aws_config):
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
    elogger.debug('trying bucket connection')
    s3_object = s3.Object(bucket_name, os.path.join(aws_root_path, 'initial.txt'))
    s3_object.upload_fileobj(data)
    elogger.debug('uploaded')


# cache_max_size_gb = 3

def get_file_from_cache(fn, sha256hex):
    if not os.path.exists(cache_dir_by_value):
        os.makedirs(cache_dir_by_value)
    have = os.path.join(cache_dir_by_value, sha256hex)
    if os.path.exists(have):
        shutil.copy(have, fn)
    else:
        msg = 'Hash not in cache'
        raise KeyError(msg)


def copy_to_cache(fn, sha256hex):
    if not os.path.exists(cache_dir_by_value):
        os.makedirs(cache_dir_by_value)
    have = os.path.join(cache_dir_by_value, sha256hex)
    if not os.path.exists(have):
        shutil.copy(fn, have)


def get_object(aws_config, bucket_name, object_key, fn):
    aws_access_key_id = aws_config['aws_access_key_id']
    aws_secret_access_key = aws_config['aws_secret_access_key']
    import boto3
    s3 = boto3.resource("s3",
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key)
    aws_object = s3.Object(bucket_name, object_key)
    aws_object.download_file(fn)


def get_files_to_upload(path):
    toupload = OrderedDict()
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            rpath = os.path.join(os.path.relpath(dirpath, path), f)
            if rpath.startswith('./'):
                rpath = rpath[2:]

            if CHALLENGE_PREVIOUS_STEPS_DIR in rpath:
                continue

            toupload[rpath] = os.path.join(dirpath, f)
    return toupload


def logs_for_container(client, container_id):
    logs = ''
    container = client.containers.get(container_id)
    for c in container.logs(stdout=True, stderr=True, stream=True, timestamps=True):
        logs += c
    return logs


def upload(aws_config, toupload):
    import boto3
    from botocore.exceptions import ClientError

    bucket_name = aws_config['bucket_name']
    aws_access_key_id = aws_config['aws_access_key_id']
    aws_secret_access_key = aws_config['aws_secret_access_key']
    # aws_root_path = aws_config['path']
    aws_path_by_value = aws_config['path_by_value']

    s3 = boto3.resource("s3",
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key)

    uploaded = []
    for rpath, realfile in toupload.items():

        sha256hex = compute_sha256hex(realfile)
        copy_to_cache(realfile, sha256hex)

        # path_by_value
        object_key = os.path.join(aws_path_by_value, 'sha256', sha256hex)

        # object_key = os.path.join(aws_root_path, rpath)
        statinfo = os.stat(realfile)
        size = statinfo.st_size

        mime_type, _encoding = mimetypes.guess_type(realfile)

        if mime_type is None:
            if realfile.endswith('.yaml'):
                mime_type = 'text/yaml'
            else:
                mime_type = 'binary/octet-stream'

        aws_object = s3.Object(bucket_name, object_key)
        try:
            aws_object.load()
            # elogger.info('Object %s already exists' % rpath)
            status = 'known'
            elogger.info('%15s %8s  %s' % (status, friendly_size(size), rpath))

        except ClientError as e:
            not_found = e.response['Error']['Code'] == '404'
            if not_found:
                status = 'uploading'
                elogger.info('%15s %8s  %s' % (status, friendly_size(size), rpath))
                aws_object.upload_file(realfile, ExtraArgs={'ContentType': mime_type})

            else:
                raise

        uploaded.append(dict(object_key=object_key, bucket_name=bucket_name, size=size,
                             mime_type=mime_type, rpath=rpath, sha256hex=sha256hex))

    return uploaded


def object_exists(s3, bucket, key):
    from botocore.exceptions import ClientError
    try:
        h = s3.head_object(Bucket=bucket, Key=key)
        print h
    except ClientError as e:
        return int(e.response['Error']['Code']) != 404
    return True


def compute_sha256hex(filename):
    cmd = ['shasum', '-a', '256', filename]
    res = subprocess.check_output(cmd)
    tokens = res.split()
    h = tokens[0]
    assert len(h) == len('08c1fe03d3a6ef7dbfaccc04613ca561b11b5fd7e9d66b643436eb611dfba348')
    return h


def dtserver_report_job(token, job_id, result, stats, machine_id,
                        process_id, evaluator_version, uploaded):
    endpoint = '/take-submission'
    method = 'POST'
    data = {'job_id': job_id,
            'result': result,
            'stats': stats,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluator_version': evaluator_version,
            'uploaded': uploaded
            }
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_work_submission(token, submission_id, machine_id, process_id, evaluator_version, features, reset):
    endpoint = '/take-submission'
    method = 'GET'
    data = {'submission_id': submission_id,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluator_version': evaluator_version,
            'features': features,
            'reset': reset}
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
