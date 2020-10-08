from dataclasses import dataclass
from typing import Dict, List, NewType, Optional

import dateutil.parser
import termcolor
from zuper_commons.timing import now_utc


from .challenge import ChallengeDescription
from .challenges_constants import ChallengesConstants
from .rest import make_server_request
from .utils import pad_to_screen_length

Endpoints = ChallengesConstants.Endpoints

SubmissionID = NewType("SubmissionID", int)
UserID = NewType("UserID", int)
JobID = NewType("JobID", int)


@dataclass
class RegistryInfo:
    registry: str


def add_impersonate_info(data, impersonate):
    if impersonate is not None:
        data["impersonate"] = impersonate


def dtserver_challenge_define(token: str, yaml, force_invalidate: bool, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.challenge_define
    method = "POST"
    data = {"yaml": yaml, "force-invalidate": force_invalidate}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method, timeout=15)


def get_registry_info(token: str, impersonate: Optional[UserID] = None) -> RegistryInfo:
    endpoint = Endpoints.registry_info
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    ri = RegistryInfo(**res)

    return ri


def dtserver_auth(token, cmd, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.auth
    method = "GET"
    data = {"query": cmd}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    return res


def get_dtserver_user_info(token, impersonate: Optional[UserID] = None):
    """ Returns a dictionary with information about the user """
    endpoint = Endpoints.user_info
    method = "GET"
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


def dtserver_retire(token, submission_id: SubmissionID, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.submissions
    method = "DELETE"
    data = {"submission_id": submission_id}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_retire_same_label(token, label: str, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.submissions
    method = "DELETE"
    data = {"label": label}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_user_submissions(token, impersonate: Optional[UserID] = None):
    """ Returns a dictionary with information about the user submissions """
    endpoint = Endpoints.submissions
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    submissions = make_server_request(token, endpoint, data=data, method=method)

    for v in submissions.values():
        for k in ["date_submitted", "last_status_change"]:
            v[k] = dateutil.parser.parse(v[k])
    return submissions


def dtserver_submit2(*, token, challenges: List[str], data, impersonate: Optional[UserID] = None):
    if not isinstance(challenges, list):
        msg = "Expected a list of strings, got %s" % challenges
        raise ValueError(msg)
    endpoint = Endpoints.components
    method = "POST"
    data = {"challenges": challenges, "parameters": data}
    add_impersonate_info(data, impersonate)
    add_version_info(data)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_info(token, submission_id: SubmissionID, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.submission_single + "/%s" % submission_id
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method, suppress_user_msg=True)


def dtserver_reset_submission(
    token, submission_id: SubmissionID, step_name, impersonate: Optional[UserID] = None
):
    endpoint = Endpoints.reset_submission
    method = "POST"
    data = {"submission_id": submission_id, "step_name": step_name}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_reset_job(token, job_id, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.reset_job
    method = "POST"
    data = {"job_id": job_id}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_report_job(
    token: str,
    job_id: int,
    result: str,  # code
    stats: dict,  # <- data 1
    machine_id,
    process_id,
    evaluator_version,
    uploaded,  # <- uploaded via S3
    timeout,  # <- how long to wait for the server
    ipfs_hashes: Dict[str, str],  # <- IPFS files
    impersonate: Optional[UserID] = None,
):
    """

        uploaded: structure returned by upload_files(directory, aws_config)
         which uses S3

        ipfs_hashes: the files represented by IPFS
            filename -> IPFS hash
    """
    endpoint = Endpoints.take_submission
    method = "POST"
    data = {
        "job_id": job_id,
        "result": result,
        "stats": stats,
        "machine_id": machine_id,
        "process_id": process_id,
        "evaluator_version": evaluator_version,
        "uploaded": uploaded,
        "ipfs_hashes": ipfs_hashes,
    }
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(
        token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True,
    )


def dtserver_work_submission(
    token: str,
    submission_id: Optional[SubmissionID],
    machine_id,
    process_id,
    evaluator_version,
    features,
    reset,
    timeout,
    impersonate: Optional[UserID] = None,
):
    """

        Pipeline:

        1) get a job using

            res = dtserver_work_submission(...)

        2) Take

            aws_config = res['aws_config']

        3) Use upload_files:

            uploaded = upload_files(directory, aws_config)

        4) Use your code to upload IPFS, get

            ipfs_hashes = {
                'rel/filename' : '/ipfs/<hash>'
            }

        5) Put the statistics in a "scores" dictionary.

            stats = {'metric1': 1.0, 'metric2': 2.0}

        5) Give this structure to the server using

            dtserver_report_job(...,
                uploaded=uploaded,
                ipfs_hashes_hashes,
                stats=stats)



        Used to get a job from the server.

        Returns a dict containing among others.

            aws_config: credentials to pass to upload_files

    """
    endpoint = Endpoints.take_submission
    method = "GET"
    data = {
        "submission_id": submission_id,
        "machine_id": machine_id,
        "process_id": process_id,
        "evaluator_version": evaluator_version,
        "features": features,
        "reset": reset,
    }
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(
        token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True,
    )


def dtserver_job_heartbeat(
    token: str,
    job_id: JobID,
    machine_id,
    process_id,
    evaluator_version,
    impersonate: Optional[UserID] = None,
):

    endpoint = Endpoints.job_heartbeat
    method = "GET"
    data = {
        "job_id": job_id,
        "machine_id": machine_id,
        "process_id": process_id,
        "evaluator_version": evaluator_version,
    }
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    timeout = 10
    return make_server_request(
        token, endpoint, data=data, method=method, timeout=timeout, suppress_user_msg=True,
    )


def get_challenge_description(
    token, challenge_name: str, impersonate: Optional[UserID] = None
) -> ChallengeDescription:
    if not isinstance(challenge_name, str):
        msg = "Expected a string for the challenge name, I got %s" % challenge_name
        raise ValueError(msg)
    endpoint = Endpoints.challenges + "/%s/description" % challenge_name
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    cd = ChallengeDescription.from_yaml(res["challenge"])
    return cd


def dtserver_get_challenges(token, impersonate: Optional[UserID] = None) -> Dict[int, ChallengeDescription]:
    endpoint = Endpoints.challenges
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    r = {}
    for challenge_id, challenge_desc in res.items():
        cd = ChallengeDescription.from_yaml(challenge_desc)
        r[challenge_id] = cd
    return r


# noinspection PyBroadException
def add_version_info(data):
    try:
        data["versions"] = get_packages_version()
    except:
        pass


# noinspection PyUnresolvedReferences,PyBroadException
def get_packages_version():
    try:
        from pip import get_installed_distributions
    except:
        from pip._internal.utils.misc import get_installed_distributions

    packages = {}
    for i in get_installed_distributions(local_only=False):
        pkg = {"version": i._version, "location": i.location}
        packages[i.project_name] = pkg

        # assert isinstance(i, (pkg_resources.EggInfoDistribution, pkg_resources.DistInfoDistribution))
    return packages


@dataclass
class CompatibleChallenges:
    available_submit: Dict[str, ChallengeDescription]
    compatible: List[str]


def dtserver_get_compatible_challenges(
    *, token: str, impersonate: Optional[int], submission_protocols: List[str]
) -> CompatibleChallenges:
    """
    Returns the list of compatible challenges for the protocols specified.
    """
    challenges = dtserver_get_challenges(token=token, impersonate=impersonate)
    compatible = []
    print("Looking for compatible and open challenges: \n")

    fmt = "  %s  %-32s  %-10s    %s"
    print(fmt % ("%-32s" % "name", "protocol", "open?", "title"))
    print(fmt % ("%-32s" % "----", "--------", "-----", "-----"))

    # S = sorted(challenges, key=lambda _: tuple(challenges[_].name.split("_-")))
    S = list(challenges)
    res = {}
    for challenge_id in S:
        cd = challenges[challenge_id]
        challenge_name = cd.name
        is_open = cd.date_open < now_utc() < cd.date_close
        if not is_open:
            continue

        is_compatible = cd.protocol in submission_protocols
        s = "open" if is_open else "closed"

        res[challenge_name] = cd
        if is_compatible:
            compatible.append(challenge_name)
            challenge_name_s = termcolor.colored(challenge_name, "blue")
        else:
            challenge_name_s = challenge_name

        challenge_name_s = pad_to_screen_length(challenge_name_s, 32)
        s2 = fmt % (challenge_name_s, cd.protocol, s, cd.title)
        print(s2)

    print("")
    print("")
    q = lambda x: termcolor.colored(x, "blue")
    for challenge_id, challenge in challenges.items():
        if challenge.closure:
            others = ", ".join(map(q, challenge.closure))
            msg = f"* Submitting to {q(challenge.name)} will also submit to: {others}."
            print(msg)
    print("")
    return CompatibleChallenges(res, compatible)
