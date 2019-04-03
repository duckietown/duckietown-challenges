from dataclasses import dataclass
from typing import *

import dateutil.parser

from duckietown_challenges import ChallengesConstants
from duckietown_challenges.challenge import ChallengeDescription
from .rest import make_server_request

Endpoints = ChallengesConstants.Endpoints


@dataclass
class RegistryInfo:
    registry: str


def dtserver_challenge_define(token, yaml, force_invalidate):
    endpoint = Endpoints.challenge_define
    method = 'POST'
    data = {'yaml': yaml, 'force-invalidate': force_invalidate}
    return make_server_request(token, endpoint, data=data, method=method,
                               timeout=15)


def get_registry_info(token) -> RegistryInfo:
    endpoint = Endpoints.registry_info
    method = 'GET'
    data = {}
    res = make_server_request(token, endpoint, data=data, method=method)
    ri = RegistryInfo(**res)
    return ri


def get_dtserver_user_info(token):
    """ Returns a dictionary with information about the user """
    endpoint = Endpoints.user_info
    method = 'GET'
    data = None
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_submit(token, queue, data):
    endpoint = Endpoints.submissions
    method = 'POST'
    data = {'queue': queue, 'parameters': data}
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_retire(token, submission_id):
    endpoint = Endpoints.submissions
    method = 'DELETE'
    data = {'submission_id': submission_id}
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_user_submissions(token):
    """ Returns a dictionary with information about the user submissions """
    endpoint = Endpoints.submissions
    method = 'GET'
    data = {}
    submissions = make_server_request(token, endpoint, data=data, method=method)

    for v in submissions.values():
        for k in ['date_submitted', 'last_status_change']:
            v[k] = dateutil.parser.parse(v[k])
    return submissions


def dtserver_submit2(*, token, challenges: List[str], data, impersonate=None):
    endpoint = Endpoints.components
    method = 'POST'
    data = {'challenges': challenges, 'parameters': data}
    if impersonate is not None:
        data['submitter_id'] = impersonate
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_info(token, submission_id):
    endpoint = Endpoints.submission_single + '/%s' % submission_id
    method = 'GET'
    data = {}
    try:
        return make_server_request(token, endpoint, data=data, method=method, suppress_user_msg=True)
    except:
        return make_server_request(token, endpoint, data=data, method=method)


def dtserver_reset_submission(token, submission_id, step_name):
    endpoint = Endpoints.reset_submission
    method = 'POST'
    data = {'submission_id': submission_id, 'step_name': step_name}
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_reset_job(token, job_id):
    endpoint = Endpoints.reset_job
    method = 'POST'
    data = {'job_id': job_id}
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_report_job(token, job_id, result, stats, machine_id,
                        process_id, evaluator_version, uploaded, timeout):
    endpoint = Endpoints.take_submission
    method = 'POST'
    data = {'job_id': job_id,
            'result': result,
            'stats': stats,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluator_version': evaluator_version,
            'uploaded': uploaded
            }
    try:
        return make_server_request(token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True)
    except:
        return make_server_request(token, endpoint, data=data, method=method, timeout=timeout)


def dtserver_work_submission(token, submission_id, machine_id, process_id, evaluator_version, features, reset, timeout):
    endpoint = Endpoints.take_submission
    method = 'GET'
    data = {'submission_id': submission_id,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluator_version': evaluator_version,
            'features': features,
            'reset': reset}

    return make_server_request(token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True)


def get_challenge_description(token, challenge_name: str) -> ChallengeDescription:
    if not isinstance(challenge_name, str):
        raise ValueError(challenge_name)
    endpoint = Endpoints.challenges + '/%s/description' % challenge_name
    method = 'GET'
    data = {}
    res = make_server_request(token, endpoint, data=data, method=method)
    cd = ChallengeDescription.from_yaml(res['challenge'])
    return cd
