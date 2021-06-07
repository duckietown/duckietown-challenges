from dataclasses import dataclass
from typing import Dict, List, Optional, TypedDict, Union

import dateutil.parser
import termcolor
from zuper_commons.timing import now_utc
from zuper_commons.types import ZValueError

from .challenge import ChallengeDescription, EvaluationParametersDict
from .challenges_constants import ChallengesConstants
from .rest import make_server_request
from .types import (
    ChallengeID,
    ChallengeName,
    ChallengeStepID,
    ComponentID,
    JobID,
    JobStatusString,
    RPath,
    StepName,
    SubmissionID,
    UserID,
)
from .utils import pad_to_screen_length

Endpoints = ChallengesConstants.Endpoints


class VersionInfo(TypedDict):
    version: str
    location: str


@dataclass
class RegistryInfo:
    registry: str


def add_impersonate_info(data, impersonate):
    if impersonate is not None:
        data["impersonate"] = impersonate


class ChallengeDefineRequestDict(TypedDict):
    yaml: str
    force_invalidate: bool


class ChallengeDefineResponseDict(TypedDict):
    challenge_id: ChallengeID
    steps_updated: Dict[StepName, str]


def dtserver_challenge_define(
    token: str,
    yaml,
    force_invalidate: bool,
    impersonate: Optional[UserID] = None,
    timeout: Optional[float] = 60,
) -> ChallengeDefineResponseDict:
    endpoint = Endpoints.challenge_define
    method = "POST"
    data: ChallengeDefineRequestDict
    data = {"yaml": yaml, "force_invalidate": force_invalidate}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method, timeout=timeout)


class RegistryInfoRequestDict(TypedDict):
    pass


class RegistryInfoResponseDict(TypedDict):
    pass


def get_registry_info(token: str, impersonate: Optional[UserID] = None) -> RegistryInfo:
    endpoint = Endpoints.registry_info
    method = "GET"
    data: RegistryInfoRequestDict
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res: RegistryInfoResponseDict = make_server_request(token, endpoint, data=data, method=method)
    ri = RegistryInfo(**res)

    return ri


class AuthRequestDict(TypedDict):
    query: str


class AuthResponseDict(TypedDict):
    results: List[dict]
    pass


def dtserver_auth(token: str, cmd: str, impersonate: Optional[UserID] = None) -> AuthResponseDict:
    endpoint = Endpoints.auth
    method = "GET"
    data: AuthRequestDict
    data = {"query": cmd}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    return res


class UserInfoRequestDict(TypedDict):
    pass


class UserInfoResponseDict(TypedDict):
    uid: int
    user_login: str
    profile: str
    name: str


def get_dtserver_user_info(token: str, impersonate: Optional[UserID] = None) -> UserInfoResponseDict:
    """Returns a dictionary with information about the user"""
    endpoint = Endpoints.user_info
    method = "GET"
    data: UserInfoRequestDict
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


class RetireRequestDict(TypedDict):
    submission_id: SubmissionID


class RetireResponseDict(TypedDict):
    pass


def dtserver_retire(
    token: str, submission_id: SubmissionID, impersonate: Optional[UserID] = None
) -> RetireResponseDict:
    endpoint = Endpoints.submissions
    method = "DELETE"
    data: RetireRequestDict
    data = {"submission_id": submission_id}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


class RetireSameLabelRequestDict(TypedDict):
    label: str
    challenges: List[ChallengeName]


class RetireSameLabelResponseDict(TypedDict):
    pass


def dtserver_retire_same_label(
    token: str, label: str, impersonate: Optional[UserID] = None, challenges: List[ChallengeName] = None
) -> RetireSameLabelResponseDict:
    if challenges is None:
        challenges = []
    endpoint = Endpoints.submissions
    method = "DELETE"
    data: RetireSameLabelRequestDict
    data = {"label": label, "challenges": challenges}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


class GetUserSubmissionRequestDict(TypedDict):
    pass


#
# class  GetUserSubmissionResponseDict(TypedDict):
#     pass


def dtserver_get_user_submissions(token: str, impersonate: Optional[UserID] = None):
    """Returns a dictionary with information about the user submissions"""
    endpoint = Endpoints.submissions
    method = "GET"
    data: GetUserSubmissionRequestDict
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)

    submissions = make_server_request(token, endpoint, data=data, method=method)
    # submissions = cast(GetUserSubmissionResponseDict, submissions)
    for v in submissions.values():
        for k in ["date_submitted", "last_status_change"]:
            v[k] = dateutil.parser.parse(v[k])
    return submissions


class SubmissionDict(TypedDict):
    submission_id: SubmissionID
    complete: bool
    status: str
    challenge_id: int
    challenge_name: str
    challenge_is_open: int
    user_label: str
    user_metadata: str


# dict[11]
#       │ │ submission_id: 12746
#       │ │ complete: True
#       │ │ status: success
#       │ │ date_submitted: 2020-12-04 12:18:45
#       │ │ last_status_change: 2020-12-04 13:24:34
#       │ │ parameters: {hash: sha256:e985e65204be87ca534d06cf6eba77143089db4b422bdeccc318577ffa0e6355}
#       │ │ challenge_id: 87
#       │ │ challenge_name: aido5-LF-sim-validation
#       │ │ challenge_is_open: 0
#       │ │ user_label: JetBrains Research
#       │ │ user_metadata: {}


def dtserver_get_submissions(
    token: str,
    challenge_name: Optional[ChallengeName],
    user_id: Optional[UserID],
    impersonate: Optional[UserID] = None,
):
    """Returns a dictionary with information about the submissions"""
    endpoint = Endpoints.submissions
    method = "GET"
    data: GetUserSubmissionRequestDict
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    query_string = {}
    if challenge_name is not None:
        query_string["challenge_name"] = challenge_name
    if user_id is not None:
        query_string["user_id"] = user_id

    submissions = make_server_request(token, endpoint, data=data, method=method, query_string=query_string)
    # submissions = cast(GetUserSubmissionResponseDict, submissions)
    for v in submissions.values():
        for k in ["date_submitted", "last_status_change"]:
            v[k] = dateutil.parser.parse(v[k])
    return submissions


# data = {
#     "image": dataclasses.asdict(br),
#     "user_label": sub_info.user_label,
#     "user_payload": sub_info.user_metadata,
#     "protocols": sub_info.protocols,
#     "retire_same_label": retire_same_label,
#     "user_priority": priority,
# }
#
class SubmitDataDict:
    image: object
    user_label: Optional[str]
    user_payload: Dict[str, object]
    protocols: List[str]
    retire_same_label: bool
    user_priority: int


class Submit2RequestDict(TypedDict):
    challenges: List[ChallengeName]
    parameters: SubmitDataDict


class ChallengeInfoDict(TypedDict):
    title: str
    queue_name: ChallengeName  ## XXX: redundan


class SubmissionDict(TypedDict):
    submission_id: SubmissionID
    existing: bool
    challenge: ChallengeInfoDict


class Submit2ResponseDict(TypedDict):
    component_id: int
    submissions: Dict[ChallengeName, SubmissionDict]


class AddSubmissionRequest(TypedDict):
    component_id: ComponentID
    challenge_names: List[ChallengeName]
    user_priority: int


def dtserver_submit2(
    *,
    token: str,
    challenges: List[ChallengeName],
    data: SubmitDataDict,
    impersonate: Optional[UserID] = None,
) -> Submit2ResponseDict:
    if not isinstance(challenges, list):
        msg = "Expected a list of strings"
        raise ZValueError(msg, challenges=challenges)
    endpoint = Endpoints.components
    method = "POST"
    data = {"challenges": challenges, "parameters": data}
    add_impersonate_info(data, impersonate)
    add_version_info(data)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_get_info(token, submission_id: SubmissionID, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.submission_single + f"/{submission_id}"
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method, suppress_user_msg=True)


def dtserver_reset_submission(
    token: str, submission_id: SubmissionID, step_name: StepName, impersonate: Optional[UserID] = None
):
    endpoint = Endpoints.reset_submission
    method = "POST"
    data = {"submission_id": submission_id, "step_name": step_name}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


def dtserver_reset_job(token: str, job_id: JobID, impersonate: Optional[UserID] = None):
    endpoint = Endpoints.reset_job
    method = "POST"
    data = {"job_id": job_id}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    return make_server_request(token, endpoint, data=data, method=method)


class StatsDict(TypedDict):
    scores: Dict[str, object]
    msg: str


def dtserver_report_job(
    token: str,
    job_id: JobID,
    result: JobStatusString,  # code
    stats: StatsDict,  # <- data 1
    machine_id: str,
    process_id: str,
    evaluator_version: str,
    uploaded: "List[ArtefactDict]",  # <- uploaded via S3
    timeout: Optional[int],  # <- how long to wait for the server
    ipfs_hashes: Dict[str, str],  # <- IPFS files
    impersonate: Optional[UserID] = None,
):
    """
    result: JobStatusString, one of ChallengesConstants.ALLOWED_JOB_STATUS
        success, failed, error, aborted, host-error

    uploaded: structure returned by upload_files(directory, aws_config)
     which uses S3

    ipfs_hashes: the files represented by IPFS
        filename -> IPFS hash

        keep empty


    for example :
        status = 'success'
        stats = {'msg': 'ok', 'scores': {}}


        status = 'failed'
        stats = {'msg': 'why it failed', 'scores': {}}
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
        token,
        endpoint,
        data=data,
        method=method,
        timeout=timeout,
        suppress_user_msg=True,
    )


class AWSConfig(TypedDict):
    bucket_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    path_by_value: str
    path: str


class S3ObjectDict(TypedDict):
    object_key: str
    bucket_name: str
    url: str


class UploadStorage(TypedDict):
    s3: S3ObjectDict


@dataclass
class ArtefactDict(TypedDict):
    size: int
    mime_type: str
    rpath: RPath
    sha256hex: str
    storage: UploadStorage


EvaluatorFeaturesDict = Dict[str, Union[str, int, float, bool]]


class WorkSubmissionRequestDict(TypedDict):
    submission_id: Optional[SubmissionID]
    machine_id: str
    process_id: str
    evaluator_version: str

    reset: bool

    features: EvaluatorFeaturesDict


class ContainerLocationDict(TypedDict):
    container_location_id: int

    created_by_user_id: UserID
    when_created: str  # iso format

    digest: str

    registry: str
    organization: str
    repository: str
    tag: str


class WorkSubmissionResultParamsDict(TypedDict):
    image_digest: str
    """ A hash uniquely defining the submission """

    locations: List[ContainerLocationDict]
    """ one or more locations. Just use first one... """


class WorkSubmissionResultDict(TypedDict):
    job_id: JobID
    """ ONLY important thing to keep, because you need for the report step. """

    step_id: ChallengeStepID
    """ for internal/book-keeping only """
    step_name: StepName
    """ for internal/book-keeping only """
    submission_id: SubmissionID
    """ for internal/book-keeping only """

    challenge_id: ChallengeID
    """ for internal/book-keeping only """
    challenge_name: ChallengeName
    """ for internal/book-keeping only """

    parameters: WorkSubmissionResultParamsDict
    """ contains the submission's info """

    challenge_parameters: EvaluationParametersDict
    """ Contains the "docker-compose"-like definitions. """

    protocol: str
    """ magic protocol string """

    aws_config: Optional[AWSConfig]
    """ Contains the AWS S3 configuration to upload files. goes straight to upload_files  """

    steps2artefacts: Dict[StepName, Dict[RPath, ArtefactDict]]
    """ if there were previous steps, it contains the output of those steps """

    steps2scores: Dict[StepName, Dict[str, object]]
    """ if there were previous steps, it contains the scores from those steps """

    timeout: float
    """ Timeout for the evaluation process """

    submitter_name: str
    """ nice string with the submitter name """


def dtserver_work_submission(
    token: str,
    submission_id: Optional[SubmissionID],
    machine_id: str,
    process_id: str,
    evaluator_version: str,
    features: EvaluatorFeaturesDict,
    reset: bool,
    timeout: Optional[int],
    impersonate: Optional[UserID] = None,
) -> WorkSubmissionResultDict:
    """
    token: Duckietown token

    submission_id: if None, get any submission. If set, try to get that one.
    reset: if submission already evaluated, reset the previous jobs.

    features: dictionary of "features - these are well known

    example:

        features:
            map_aido5_large_loop: 1
            nduckiebots: 3
            nduckies: 20

    machine_id, process_id, evaluator_version: identify the identity of the evaluator.
    machine_id, process_id: free form - valid identifier
    evaluator_version = duckietown_challenges_runner.__version__


    timeout: connection timeout
    impersonate: ID to impersonate if any


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
    data: WorkSubmissionRequestDict
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
        token,
        endpoint,
        data=data,
        method=method,
        timeout=timeout,
        suppress_user_msg=True,
    )


class HeartbeatRequestDict(TypedDict):
    job_id: JobID
    machine_id: str
    process_id: str
    evaluator_version: str
    uploaded: List[ArtefactDict]

    versions: Dict[str, VersionInfo]
    features: EvaluatorFeaturesDict


class HeartbeatResponseDict(TypedDict):
    abort: bool
    why: Optional[str]


def dtserver_job_heartbeat(
    token: str,
    job_id: JobID,
    machine_id: str,
    process_id: str,
    evaluator_version: str,
    uploaded: List[ArtefactDict],
    features: EvaluatorFeaturesDict,
    impersonate: Optional[UserID] = None,
    query_string: str = None,
) -> HeartbeatResponseDict:
    """
    You just call every 30 seconds.

    Optionally you can already send some uploaded files.


    """
    endpoint = Endpoints.job_heartbeat
    method = "GET"
    data: HeartbeatRequestDict
    data = {
        "machine_id": machine_id,
        "process_id": process_id,
        "evaluator_version": evaluator_version,
        "features": features,
        "versions": get_packages_version(),
        "job_id": job_id,
        "uploaded": uploaded,
    }
    # add_version_info(data)
    add_impersonate_info(data, impersonate)
    timeout = 10
    return make_server_request(
        token,
        endpoint,
        data=data,
        method=method,
        timeout=timeout,
        suppress_user_msg=True,
        query_string=query_string,
    )


def get_challenge_description(
    token: str, challenge_name: ChallengeName, impersonate: Optional[UserID] = None
) -> ChallengeDescription:
    if not isinstance(challenge_name, str):
        msg = "Expected a string for the challenge name, I got %s" % challenge_name
        raise ValueError(msg)
    endpoint = Endpoints.challenges + f"/{challenge_name}/description"
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    cd = ChallengeDescription.from_yaml(res["challenge"])
    return cd


def dtserver_get_challenges(
    token: str, impersonate: Optional[UserID] = None
) -> Dict[int, ChallengeDescription]:
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


class JobInfoDict(TypedDict):
    challenge_name: ChallengeName
    job_id: int
    step_id: int
    status: str
    uptodate: int
    artefacts: Dict[RPath, ArtefactDict]
    why: Optional[str]


def dtserver_get_job(
    token: str,
    job_id: JobID,
    impersonate: Optional[UserID] = None,
) -> JobInfoDict:
    endpoint = Endpoints.jobs + f"/{job_id}"
    method = "GET"
    data = {}
    add_version_info(data)
    add_impersonate_info(data, impersonate)
    res = make_server_request(token, endpoint, data=data, method=method)
    return res


# noinspection PyBroadException
def add_version_info(data):
    try:
        data["versions"] = get_packages_version()
    except:
        pass


# noinspection PyUnresolvedReferences,PyBroadException,PyCompatibility,PyProtectedMember
def get_packages_version() -> Dict[str, VersionInfo]:
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
    available_submit: Dict[ChallengeName, ChallengeDescription]
    compatible: List[ChallengeName]


def dtserver_get_compatible_challenges(
    *, token: str, impersonate: Optional[int], submission_protocols: List[str], quiet: bool = False
) -> CompatibleChallenges:
    """
    Returns the list of compatible challenges for the protocols specified.
    """
    challenges = dtserver_get_challenges(token=token, impersonate=impersonate)
    compatible = []

    def mprint(x):
        if not quiet:
            print(x)

    mprint("Looking for compatible and open challenges: \n")

    fmt = "  %s  %-32s  %-10s    %s"
    mprint(fmt % ("%-32s" % "name", "protocol", "open?", "title"))
    mprint(fmt % ("%-32s" % "----", "--------", "-----", "-----"))

    # S = sorted(challenges, key=lambda _: tuple(challenges[_].name.split("_-")))
    S = list(challenges)
    res: Dict[ChallengeName, ChallengeDescription]
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
        mprint(s2)

    mprint("")
    mprint("")
    q = lambda x: termcolor.colored(x, "blue")
    for challenge_id, challenge in challenges.items():
        if challenge.closure:
            others = ", ".join(map(q, challenge.closure))
            # msg = f"* Submitting to {q(challenge.name)} will also submit to: {others}."
            # mprint(msg)
    mprint("")
    return CompatibleChallenges(res, compatible)
