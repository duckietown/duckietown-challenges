# coding=utf-8
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, cast, Dict, List, Optional, Tuple, Union

import yaml
from dateutil.tz import tzutc
from networkx import ancestors, DiGraph
from zuper_ipce import ipce_from_object, object_from_ipce

from .challenges_constants import ChallengesConstants, JobStatusString, StepName
from .cmd_submit_build import parse_complete_tag
from .exceptions import InvalidConfiguration
from .utils import indent, safe_yaml_dump, wrap_config_reader2

__all__ = [
    "ChallengeDescription",
    "EvaluationParameters",
    "ChallengesConstants",
    "ChallengeStep",
    "ChallengeTransitions",
    "ChallengeDependency",
    "InvalidChallengeDescription",
    "Scoring",
    "Score",
    "SubmissionDescription",
    "ServiceDefinition",
]


class InvalidChallengeDescription(Exception):
    pass


# these are job statuses
STATE_START = "START"
STATE_ERROR = "ERROR"
STATE_SUCCESS = "SUCCESS"
STATE_FAILED = "FAILED"

ALLOWED_CONDITION_TRIGGERS = ChallengesConstants.ALLOWED_JOB_STATUS


@dataclass(repr=False)
class Build:
    context: str
    dockerfile: str
    args: Dict[str, Any]

    #
    # def __init__(self, context, dockerfile, args):
    #     self.context = context
    #     self.dockerfile = dockerfile
    #     self.args = args

    def __repr__(self):
        return nice_repr(self)

    def as_dict(self):
        return dict(context=self.context, dockerfile=self.dockerfile, args=self.args)

    @classmethod
    def from_yaml(cls, d0):
        if not isinstance(d0, dict):
            msg = "Expected dict, got %s" % d0.__repr__()
            raise ValueError(msg)
        d = dict(**d0)

        context = d.pop("context", ".")
        dockerfile = d.pop("dockerfile", "Dockerfile")
        args = d.pop("args", {})

        if d:
            msg = "Extra fields: %s" % list(d0)
            raise ValueError(msg)
        return Build(context, dockerfile, args)


@dataclass
class PortDefinition:
    external: Optional[int]
    internal: int


@dataclass
class ServiceDefinition:
    image: Optional[str]
    build: Optional[Build]
    environment: Dict[str, Any]
    ports: List[PortDefinition]

    def __repr__(self):
        return nice_repr(self)

    def equivalent(self, other):
        if self.image != ChallengesConstants.SUBMISSION_CONTAINER_TAG:
            br2 = parse_complete_tag(other.image)

            try:
                br1 = parse_complete_tag(self.image)
            except ValueError as e:
                msg = "Could not even parse mine"
                raise NotEquivalent(msg) from e

            if br1.digest is None or br2.digest is None:
                msg = "No digest information, assuming different.\nself: %s\nother: %s" % (br1, br2)
                raise NotEquivalent(msg)
            if br1.digest != br2.digest:
                msg = "Different digests:\n\n  %s\n\n  %s" % (br1, br2)
                raise NotEquivalent(msg)
            if self.ports != other.ports:
                msg = "Different digests:\n\n  %s\n\n  %s" % (br1, br2)
                raise NotEquivalent(msg)

        if self.environment != other.environment:
            msg = "Different environments:\n\n %s\n\n  %s" % (self.environment, other.environment,)
            raise NotEquivalent(msg)

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d0):
        image = d0.pop("image", None)
        environment = d0.pop("environment", {})
        if environment is None:
            environment = {}

        if "build" in d0:
            build = d0.pop("build")
            if build is not None:
                build = Build.from_yaml(build)
        else:
            build = None

        if build and image:
            msg = 'Cannot specify both "build" and "image".'
            raise ValueError(msg)

        image_digest = d0.pop("image_digest", None)
        if image_digest:
            image = f"{image}@{image_digest}"

        for k, v in list(environment.items()):
            if "-" in k:
                msg = 'Invalid environment variable "%s" should not contain a space.' % k
                raise InvalidConfiguration(msg)

            if isinstance(v, (int, float)):
                environment[k] = str(v)
            elif isinstance(v, str):
                pass
            elif isinstance(v, dict):
                # interpret as tring
                s = yaml.safe_dump(v)
                environment[k] = s
            else:
                msg = f'The type {type(v).__name__} is not allowed for environment variable "{k}".'
                raise InvalidConfiguration(msg)
        ports_ = d0.pop("ports", [])
        ports = []
        for s in ports_:
            if isinstance(s, int):
                internal = s
                external = None
            elif isinstance(s, dict):
                internal = s.get("internal", None)
                external = s.get("internal", None)
            elif isinstance(s, str):
                if not ":" in s:
                    # raise InvalidConfiguration(s)
                    internal = int(s)
                    external = None
                else:
                    tokens = s.split(":")
                    external = int(tokens[0])
                    internal = int(tokens[1])
            else:
                raise ValueError(repr(ports_))
            ports.append(PortDefinition(external=external, internal=internal))
        return ServiceDefinition(image=image, environment=environment, build=build, ports=ports)

    def as_dict(self):

        res = dict(image=self.image, environment=self.environment)

        ports = []
        for p in self.ports:
            if p.external is not None:
                ports.append(f"{p.external}:{p.internal}")
            else:
                ports.append(f"{p.internal}")

        if ports:
            res["ports"] = ports
        if self.build:
            res["build"] = self.build.as_dict()
        else:
            pass

        return res


@dataclass
class EvaluationParameters:
    """
        You can specify these fields for the docker file:

            version: '3'

            services:
                evaluator:
                    image: imagename
                    environment:
                        var: var
                solution: # For the solution container
                    image: SUBMISSION_CONTAINER
                    environment:
                        var: var

    """

    version: str
    services: Dict[str, ServiceDefinition]

    def __init__(self, version, services):
        self.version = version
        self.services = services

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d):

        services_ = d.pop("services")
        if not isinstance(services_, dict):
            msg = "Expected dict got %s" % services_.__repr__()
            raise ValueError(msg)

        if not services_:
            msg = "No services described."
            raise ValueError(msg)

        version = d.pop("version", "3")

        services = {}
        for k, v in services_.items():
            services[k] = ServiceDefinition.from_yaml(v)

        # check that there is at least a service with the image called
        # SUBMISSION_CONTAINER
        n = 0
        for service_definition in services.values():
            if service_definition.image == ChallengesConstants.SUBMISSION_CONTAINER_TAG:
                n += 1
        # if n == 0:
        #     msg = 'I expect one of the services to have "image: %s".' % SUBMISSION_CONTAINER_TAG
        #     raise ValueError(msg)
        # if n > 1:
        #     msg = 'Too many services with  "image: %s".' % SUBMISSION_CONTAINER_TAG
        #     raise ValueError(msg)

        return EvaluationParameters(services=services, version=version)

    def __repr__(self):
        return nice_repr(self)

    def as_dict(self):
        services = dict([(k, v.as_dict()) for k, v in self.services.items()])
        return dict(version=self.version, services=services)

    def equivalent(self, other):
        if set(other.services) != set(self.services):
            msg = "Different set of services."
            raise NotEquivalent(msg)
        for s in other.services:
            try:
                self.services[s].equivalent(other.services[s])
            except NotEquivalent as e:
                msg = "Service %r differs:\n\n%s" % (s, indent(e, "  "))
                raise NotEquivalent(msg)


@dataclass
class ChallengeStep:
    name: str
    title: str
    description: str
    evaluation_parameters: EvaluationParameters
    features_required: Dict[str, Any]
    timeout: int
    uptodate_token: Optional[str] = None

    def as_dict(self):
        data = {}
        data["title"] = self.title
        data["description"] = self.description
        data["evaluation_parameters"] = self.evaluation_parameters.as_dict()
        data["features_required"] = self.features_required
        data["timeout"] = self.timeout
        data["uptodate_token"] = self.uptodate_token
        return data

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, data, name):
        title = data.pop("title")
        description = data.pop("description")
        evaluation_parameters = EvaluationParameters.from_yaml(data.pop("evaluation_parameters"))
        features_required = data.pop("features_required", {})
        timeout = data.pop("timeout")
        uptodate_token = data.pop("uptodate_token", None)
        return ChallengeStep(
            name,
            title,
            description,
            evaluation_parameters,
            features_required,
            timeout=timeout,
            uptodate_token=uptodate_token,
        )


class NotEquivalent(Exception):
    pass


def nice_repr(x):
    K = type(x).__name__
    return "%s\n\n%s" % (K, indent(safe_yaml_dump(x.as_dict()), "   "))


# Transition = namedtuple("Transition", "first condition second")
@dataclass
class Transition:
    first: str
    condition: str
    second: str


class InvalidSteps(Exception):
    pass


@dataclass(repr=False)
class ChallengeTransitions:
    steps: List[str]
    transitions: List[Transition]

    #
    # def __init__(self, transitions, steps):
    #     self.transitions = []
    #     self.steps = steps
    #     for first, condition, second in self.transitions:
    #         assert first == STATE_START or first in self.steps, first
    #         assert second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS] or second in self.steps, second
    #         assert condition in ALLOWED_CONDITION_TRIGGERS, condition
    #         self.transitions.append(Transition(first, condition, second))

    def as_list(self):
        res = []
        for transition in self.transitions:
            res.append([transition.first, transition.condition, transition.second])
        return res

    def __repr__(self):
        return "\n".join(self.steps_explanation())

    def steps_explanation(self):
        ts = []
        for t in self.transitions:
            if t.first == STATE_START:
                ts.append(f"At the beginning execute step `{t.second}`.")
            else:
                if t.second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                    ts.append(
                        f"If step `{t.first}` finishes with status `{t.condition}`, then declare the "
                        f"submission `{t.second}`."
                    )
                else:
                    ts.append(
                        f"If step `{t.first}` finishes with status `{t.condition}`, then execute step `"
                        f"{t.second}`."
                    )
        return ts

    def top_ordered(self):
        _G = self.get_graph()  # XXX
        return list(self.steps)

    def get_graph(self) -> DiGraph:
        G = DiGraph()
        for t in self.transitions:
            G.add_edge(t.first, t.second)
        return G

    def get_precs(self, x: str) -> List[str]:
        G = self.get_graph()
        res = list(ancestors(G, x))
        # print('precs of %s: %s' % (x, res))
        return res

    def get_next_steps(
        self, status: Dict[StepName, JobStatusString], step2age=None
    ) -> Tuple[bool, Optional[str], List[StepName]]:
        """ status is a dictionary from step name to status.

            It contains at the beginning

                START: success

            Returns:
                 bool (completE)
                 optional status:  ['error', 'failed', 'success']
                 a list of steps to activate next

        """
        CS = ChallengesConstants
        # dclogger.info('Received status = %s' % status)
        assert isinstance(status, dict)
        assert STATE_START in status
        assert status[STATE_START] == CS.STATUS_JOB_SUCCESS
        status = dict(**status)
        for k, ks in list(status.items()):
            if k != STATE_START and k not in self.steps:
                # msg = "Ignoring invalid step %s -> %s" % (k, ks)
                # dclogger.error(msg)
                status.pop(k)

            if ks not in ChallengesConstants.ALLOWED_JOB_STATUS:
                # msg = f"Ignoring invalid step {k} -> {ks!r}"
                # dclogger.error(msg)
                status.pop(k)

            # timeout or aborted or host error = like it never happened
            if ks in [
                CS.STATUS_JOB_TIMEOUT,
                CS.STATUS_JOB_ABORTED,
                CS.STATUS_JOB_HOST_ERROR,
            ]:
                if k in status:
                    status.pop(k)

        # make sure that the steps in which they depend are ok

        def predecessors_success(_: str) -> bool:
            precs = self.get_precs(_)
            its_age = step2age.get(_, -1) if step2age else 0
            for k2 in precs:
                pred_age = step2age.get(k2, -1) if step2age else 0
                # dclogger.debug('%s %s %s %s' % (_, its_age, k2, pred_age))
                if pred_age > its_age:
                    # dclogger.debug('Its depedency is younger')
                    return False
                if k2 not in status or status[k2] != CS.STATUS_JOB_SUCCESS:
                    return False
            return True

        to_activate = cast(List[StepName], [])
        outcomes = set()
        for t in self.transitions:
            if t.first in status and status[t.first] == t.condition and predecessors_success(t.first):
                # dclogger.debug('Transition %s is activated' % str(t))

                like_it_does_not_exist = [ChallengesConstants.STATUS_JOB_ABORTED]
                if (
                    t.second in status
                    and status[t.second] not in like_it_does_not_exist
                    and predecessors_success(t.second)
                ):
                    # dclogger.debug('Second %s already activated (and in %s)' % (t.second, status[t.second]))
                    pass
                else:
                    if t.second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                        # dclogger.debug('Finishing here')
                        outcomes.add(t.second.lower())
                        # return True, t.second.lower(), []
                    else:
                        to_activate.append(t.second)
        if outcomes:
            outcome = list(outcomes)[0]
            complete = True
        else:
            complete = False
            outcome = None

        # dclogger.debug('Incomplete; need to do: %s' % to_activate)
        return complete, outcome, to_activate


def steps_from_transitions(transitions: List[List[str]]) -> List[str]:
    steps = []
    for first, _, second in transitions:
        if first not in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
            steps.append(first)
        if second not in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
            steps.append(second)
    return steps


def from_steps_transitions(steps: List[str], transitions_str: List[List[str]]) -> ChallengeTransitions:
    transitions = []
    for first, condition, second in transitions_str:
        assert first == STATE_START or first in steps, first
        assert second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS] or second in steps, (second, steps)
        assert condition in ALLOWED_CONDITION_TRIGGERS, condition
        transitions.append(Transition(first, condition, second))
    return ChallengeTransitions(steps, transitions)


def order_from_description(description: str) -> str:
    if description == "descending":
        order = Score.HIGHER_IS_BETTER
        return order
    if description == "ascending":
        order = Score.LOWER_IS_BETTER
        return order
    raise ValueError(description)


@dataclass
class Score:
    HIGHER_IS_BETTER = "higher-is-better"
    LOWER_IS_BETTER = "lower-is-better"
    ALLOWED = [HIGHER_IS_BETTER, LOWER_IS_BETTER]

    order: str
    name: str
    description: str
    discretization: Optional[float]
    short: Optional[str]

    def __post_init__(self):
        if self.order not in Score.ALLOWED:
            msg = "Invalid value %s" % self.order
            raise ValueError(msg)

        if self.discretization is not None:
            discretization = float(self.discretization)
            if discretization <= 0:
                msg = "Need a strictly positive discretization: %s" % discretization
                raise ValueError(msg)

    def __repr__(self):
        return nice_repr(self)

    def as_dict(self):
        return dict(
            description=self.description,
            name=self.name,
            order=self.order,
            discretization=self.discretization,
            short=self.short,
        )

    @classmethod
    def from_yaml(cls, data0):
        try:
            if not isinstance(data0, dict):
                msg = "Expected dict, got %s" % type(data0).__name__
                raise InvalidChallengeDescription(msg)

            data = dict(**data0)
            short = data.pop("short", None)
            name = data.pop("name")
            description = data.pop("description", None)
            order = data.pop("order", Score.HIGHER_IS_BETTER)
            # TODO: remove
            if order == "ascending":
                order = Score.HIGHER_IS_BETTER
            if order == "descending":
                order = Score.LOWER_IS_BETTER
            if order not in Score.ALLOWED:
                msg = 'Invalid value "%s" not in %s.' % (order, Score.ALLOWED)
                raise InvalidChallengeDescription(msg)

            discretization = data.pop("discretization", None)

            if data:
                msg = "Extra keys in configuration file: %s" % list(data)
                raise InvalidChallengeDescription(msg)

            return Score(
                name=name, description=description, order=order, discretization=discretization, short=short,
            )
        except KeyError as e:
            msg = "Missing config %s" % e
            raise InvalidChallengeDescription(msg) from e


def Score_as_dict(score: Score):
    return dict(
        description=score.description,
        name=score.name,
        order=score.order,
        discretization=score.discretization,
        short=score.short,
    )


@dataclass(repr=False)
class Scoring:
    scores: List[Score]

    #
    # def as_dict(self):
    #     scores = [_.as_dict() for _ in self.scores]
    #     return dict(scores=scores)

    def __repr__(self):
        # noinspection PyTypeChecker
        return nice_repr(self)

    @classmethod
    def from_yaml(cls, data0):
        try:
            if not isinstance(data0, dict):
                msg = "Expected dict, got %s" % type(data0).__name__
                raise InvalidChallengeDescription(msg)

            data = dict(**data0)
            scores = data.pop("scores")
            if not isinstance(scores, list):
                msg = "Expected list, got %s" % type(scores).__name__
                raise InvalidChallengeDescription(msg)

            scores = [Score.from_yaml(_) for _ in scores]
            if data:
                msg = "Extra keys in configuration file: %s" % list(data)
                raise InvalidChallengeDescription(msg)

            return Scoring(scores)

        except KeyError as e:
            msg = "Missing config %s" % e
            raise InvalidChallengeDescription(msg) from e


def Scoring_as_dict(s: Scoring):
    scores = [Score_as_dict(_) for _ in s.scores]
    return dict(scores=scores)


@dataclass
class DepScore:
    description: str
    importance: float
    score_name: str
    score_min: float
    score_max: float


@dataclass
class DepBetter:
    description: str
    importance: float

    username: str
    sub_label: str


@dataclass
class ChallengeDependency:
    description: str
    min_threshold: float
    scores: Dict[str, DepScore]
    comparisons: Dict[str, DepBetter]


@dataclass
class ChallengeDescription:
    name: str
    title: str
    description: str
    protocol: str
    date_open: datetime
    date_close: datetime
    steps: Dict[str, ChallengeStep]
    transitions: List[List[str]]  # 3 elements each

    scoring: Scoring
    tags: List[str]

    dependencies: Dict[str, ChallengeDependency]

    ct: ChallengeTransitions
    closure: Optional[List[str]] = field(default_factory=list)

    def __post_init__(self):

        # check_isinstance(self.date_open, datetime)
        # check_isinstance(self.date_close, datetime)
        # dclogger.info(f'received {self.date_open.tzinfo} {id(self.date_open)}   {self.date_close.tzinfo}'
        #               f' {id(self.date_close)}  ')
        if self.date_open.tzinfo is None:
            raise ValueError(self.date_open)
        if self.date_close.tzinfo is None:
            raise ValueError(self.date_close)

    def get_next_steps(self, status):
        return self.ct.get_next_steps(status)

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, data):
        name = data.pop("challenge")
        tags = data.pop("tags", [])
        title = data.pop("title")
        description = data.pop("description")
        protocol = data.pop("protocol")

        date_open = add_timezone(data.pop("date-open"))
        date_close = add_timezone(data.pop("date-close"))

        assert date_close.tzinfo is not None, (date_close, date_open)
        assert date_open.tzinfo is not None, (date_close, date_open)
        data.pop("roles", None)

        steps = data.pop("steps")
        Steps = {}
        for k, v in steps.items():
            Steps[k] = ChallengeStep.from_yaml(v, k)

        transitions = data.pop("transitions", None)
        if transitions is None:
            if len(Steps) == 1:
                stepname = list(Steps)[0]
                transitions = [
                    [STATE_START, "success", stepname],
                    [stepname, "success", STATE_SUCCESS],
                    [stepname, "failed", STATE_FAILED],
                    [stepname, "error", STATE_ERROR],
                ]
            else:
                msg = "Need transitions if there is more than one step."
                raise ValueError(msg)

        scoring = Scoring.from_yaml(data.pop("scoring"))

        closure = data.pop("closure", [])
        dependencies_ = data.pop("dependencies", {})
        dependencies = object_from_ipce(dependencies_, Dict[str, ChallengeDependency])
        ct = from_steps_transitions(list(Steps), transitions)

        assert date_open.tzinfo is not None and date_close.tzinfo is not None
        res = ChallengeDescription(
            name=name,
            title=title,
            description=description,
            protocol=protocol,
            date_open=date_open,
            date_close=date_close,
            steps=Steps,
            transitions=transitions,
            tags=tags,
            scoring=scoring,
            dependencies=dependencies,
            ct=ct,
            closure=closure,
        )
        res.date_open = date_open
        res.date_close = date_close
        assert (res.date_open.tzinfo is not None) and (res.date_close.tzinfo is not None), (
            date_open.tzinfo,
            date_close.tzinfo,
            res.date_open.tzinfo,
            res.date_close.tzinfo,
        )
        return res

    def as_dict(self):
        data = {}
        data["challenge"] = self.name
        data["title"] = self.title
        data["description"] = self.description
        data["protocol"] = self.protocol
        data["date-open"] = self.date_open.isoformat() if self.date_open else None
        data["date-close"] = self.date_close.isoformat() if self.date_close else None
        # data['roles'] = self.roles
        data["transitions"] = []
        for t in self.ct.transitions:
            tt = [t.first, t.condition, t.second]
            data["transitions"].append(tt)
        steps = {}
        for k, v in self.steps.items():
            steps[k] = v.as_dict()
        data["steps"] = steps
        data["closure"] = self.closure
        data["tags"] = self.tags
        data["scoring"] = Scoring_as_dict(self.scoring)
        data["dependencies"] = ipce_from_object(self.dependencies, Dict[str, ChallengeDependency])
        return data

    def as_yaml(self):
        return yaml.dump(self.as_dict())

    def __repr__(self):
        return nice_repr(self)


#
# def makesure_timezone(d: Optional[datetime]) -> Optional[datetime]:
#     if d is None:
#         return d
#     else:
#         secs = time.mktime(d.timetuple())
#         return time.gmtime(secs)


def interpret_date(d: Optional[Union[datetime, date, str]]) -> Optional[datetime]:
    if d is None:
        return d
    if isinstance(d, datetime):
        return d.astimezone(tzutc())

    if isinstance(d, date):
        d = datetime.combine(d, datetime.min.time())
        return d.astimezone(tzutc())

    if isinstance(d, str):
        from dateutil import parser

        res = parser.parse(d)
        return res.astimezone(tzutc())

    raise ValueError(d.__repr__())


from dateutil import parser


def add_timezone(d: Union[str, datetime]) -> datetime:
    if isinstance(d, str):
        d = parser.parse(d)
    if d.tzinfo is not None:
        return d
    res = d.astimezone(tzutc())
    assert res.tzinfo is not None
    return res


@dataclass(repr=False)
class SubmissionDescription:
    challenge_names: Optional[List[str]]
    protocols: List[str]
    user_label: Optional[str]
    user_metadata: dict
    description: Optional[str]

    def __post_init_(self):
        if self.challenge_names is not None:
            if not isinstance(self.challenge_names, list):
                msg = "Expected a list of strings for challenge names, got %s" % self.challenge_names
                raise ValueError(msg)
        if not isinstance(self.protocols, list):
            msg = "Expected a list of strings for protocols names, got %s" % self.protocols
            raise ValueError(msg)

    def __repr__(self):
        return nice_repr(self)

    def as_dict(self):
        return dict(
            protocols=self.protocols,
            challenge_names=self.challenge_names,
            user_label=self.user_label,
            user_metadata=self.user_metadata,
            description=self.description,
        )

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, data):
        challenge_name = data.pop("challenge", None)
        if challenge_name is None:
            challenges = None
        else:
            if isinstance(challenge_name, list):
                challenges = challenge_name
            else:
                challenges = [challenge_name]

        protocol = data.pop("protocol")
        if isinstance(protocol, list):
            protocols = protocol
        else:
            protocols = [protocol]

        description = data.pop("description", None)
        user_label = data.pop("user-label", None)
        user_metadata = data.pop("user-payload", None)

        return SubmissionDescription(
            challenge_names=challenges,
            protocols=protocols,
            description=description,
            user_label=user_label,
            user_metadata=user_metadata,
        )
