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


def add_impersonate_info(data, impersonate):
    if impersonate is not None:
        data['impersonate'] = impersonate


def dtserver_challenge_define(token, yaml, force_invalidate, impersonate=None):
    endpoint = Endpoints.challenge_define
    method = 'POST'
    data = {'yaml': yaml, 'force-invalidate': force_invalidate}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method,
                               timeout=15)


def get_registry_info(token, impersonate=None) -> RegistryInfo:
    endpoint = Endpoints.registry_info
    method = 'GET'
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    ri = RegistryInfo(**res)

    return ri


def dtserver_auth(token, cmd):
    endpoint = Endpoints.auth
    method = 'GET'
    data = {'query': cmd}
    add_version_info(data)
    res = make_server_request(token, endpoint, data=data, method=method)
    return res


def get_dtserver_user_info(token, impersonate=None):
    """ Returns a dictionary with information about the user """
    endpoint = Endpoints.user_info
    method = 'GET'
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


#
# def dtserver_submit(token, queue, data):
#     endpoint = Endpoints.submissions
#     method = 'POST'
#     data = {'queue': queue, 'parameters': data}
#     add_version_info(data)
#     return make_server_request(token, endpoint, data=data, method=method)


def dtserver_retire(token, submission_id, impersonate=None):
    endpoint = Endpoints.submissions
    method = 'DELETE'
    data = {'submission_id': submission_id}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_user_submissions(token, impersonate=None):
    """ Returns a dictionary with information about the user submissions """
    endpoint = Endpoints.submissions
    method = 'GET'
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    submissions = make_server_request(token, endpoint, data=data, method=method)

    for v in submissions.values():
        for k in ['date_submitted', 'last_status_change']:
            v[k] = dateutil.parser.parse(v[k])
    return submissions


def dtserver_submit2(*, token, challenges: List[str], data, impersonate=None):
    endpoint = Endpoints.components
    method = 'POST'
    data = {'challenges': challenges, 'parameters': data}
    add_impersonate_info(data, impersonate)
    add_version_info(data)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_info(token, submission_id, impersonate=None):
    endpoint = Endpoints.submission_single + '/%s' % submission_id
    method = 'GET'
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method, suppress_user_msg=True)


def dtserver_reset_submission(token, submission_id, step_name, impersonate=None):
    endpoint = Endpoints.reset_submission
    method = 'POST'
    data = {'submission_id': submission_id, 'step_name': step_name}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_reset_job(token, job_id, impersonate=None):
    endpoint = Endpoints.reset_job
    method = 'POST'
    data = {'job_id': job_id}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
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
    add_version_info(data)
    return make_server_request(token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True)


def dtserver_work_submission(token, submission_id, machine_id, process_id, evaluator_version, features, reset, timeout):
    endpoint = Endpoints.take_submission
    method = 'GET'
    data = {'submission_id': submission_id,
            'machine_id': machine_id,
            'process_id': process_id,
            'evaluator_version': evaluator_version,
            'features': features,
            'reset': reset}
    add_version_info(data)
    return make_server_request(token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True)


def get_challenge_description(token, challenge_name: str, impersonate=None) -> ChallengeDescription:
    if not isinstance(challenge_name, str):
        raise ValueError(challenge_name)
    endpoint = Endpoints.challenges + '/%s/description' % challenge_name
    method = 'GET'
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    cd = ChallengeDescription.from_yaml(res['challenge'])
    return cd


def dtserver_get_challenges(token, impersonate=None) -> Dict[str, ChallengeDescription]:
    endpoint = Endpoints.challenges
    method = 'GET'
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    r = {}
    for challenge_id_s, challenge_desc in res.items():
        cd = ChallengeDescription.from_yaml(challenge_desc)
        r[challenge_id_s] = cd
    return r


def add_version_info(data):
    try:
        data['versions'] = get_packages_version()
    except:
        pass


def get_packages_version():
    try:
        from pip import get_installed_distributions
    except:
        from pip._internal.utils.misc import get_installed_distributions

    packages = {}
    for i in get_installed_distributions(local_only=False):
        pkg = {
            'version': i._version,
            'location': i.location
        }
        packages[i.project_name] = pkg

        # assert isinstance(i, (pkg_resources.EggInfoDistribution, pkg_resources.DistInfoDistribution))
    return packages
