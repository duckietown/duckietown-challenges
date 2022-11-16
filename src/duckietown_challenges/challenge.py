# coding=utf-8
from dataclasses import field
from datetime import date, datetime
from typing import Any, cast, Dict, Iterator, List, NewType, Optional, Tuple, TYPE_CHECKING, TypedDict, Union

import yaml
from dateutil.tz import tzutc
from duckietown_build_utils import DockerCompleteImageName
from networkx import ancestors, DiGraph

from zuper_commons.types import ZException, ZNotImplementedError, ZValueError
from zuper_ipce import ipce_from_object, object_from_ipce
from zuper_typing import dataclass, make_list

if TYPE_CHECKING:
    from dataclasses import dataclass

from .challenges_constants import ChallengesConstants
from .exceptions import InvalidConfiguration
from .types import ChallengeName, JobStatusString, ServiceName, StepName
from .utils import indent, safe_yaml_dump, wrap_config_reader2

__all__ = [
    "EvaluationParametersDict",
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
    "NotEquivalent",
    "STATE_START",
    "STATE_ERROR",
    "STATE_FAILED",
    "STATE_SUCCESS",
    "ALLOWED_CONDITION_TRIGGERS",
    "DepBetter",
    "DepScore",
    "from_steps_transitions",
    "Scoring_as_dict",
    "steps_from_transitions",
    "Transition",
    "AndCondition",
    "SimpleCondition",
    "Condition",
]


class InvalidChallengeDescription(ZException):
    pass


EvalStateString = NewType("EvalStateString", StepName)
# these are job statuses
STATE_START = cast(EvalStateString, "START")
STATE_ERROR = cast(EvalStateString, "ERROR")
STATE_SUCCESS = cast(EvalStateString, "SUCCESS")
STATE_FAILED = cast(EvalStateString, "FAILED")

ALLOWED_CONDITION_TRIGGERS: List[JobStatusString] = ChallengesConstants.ALLOWED_JOB_STATUS


@dataclass(repr=False)
class Build:
    context: str
    dockerfile: Optional[str]
    args: Dict[str, Any]

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
        dockerfile = d.pop("dockerfile", None)
        args = d.pop("args", {})

        if d:
            msg = "Extra fields: %s" % list(d0)
            raise ValueError(msg)
        return Build(context, dockerfile, args)


@dataclass
class PortDefinition:
    external: Optional[int]
    internal: int


class ServiceDefinitionDict(TypedDict):
    image: Optional[str]
    build: Optional[Build]
    environment: Dict[str, Any]
    ports: List[PortDefinition]


@dataclass
class ServiceDefinition:
    image: Optional[str]
    build: Optional[Build]
    environment: Dict[str, str]
    ports: List[PortDefinition]

    def __repr__(self):
        return nice_repr(self)

    def equivalent(self, other):
        if self.image != ChallengesConstants.SUBMISSION_CONTAINER_TAG:
            from duckietown_build_utils import parse_complete_tag, DockerCompleteImageName  # FIXME

            br2 = parse_complete_tag(other.image)

            try:
                br1 = parse_complete_tag(DockerCompleteImageName(self.image))
            except ValueError as e:
                msg = "Could not even parse mine"
                raise NotEquivalent(msg) from e

            if br1.digest is None or br2.digest is None:
                msg = "No digest information, assuming different."
                raise NotEquivalent(msg, br1=br1, br2=br2)
            if br1.digest != br2.digest:
                msg = "Different digests"
                raise NotEquivalent(msg, br1=br1, br2=br2)
            if self.ports != other.ports:
                msg = "Different ports"
                raise NotEquivalent(msg, mine=self.ports, other=self.ports)

        if self.environment != other.environment:
            msg = "Different environments"
            raise NotEquivalent(msg, mine=self.environment, other=other.environment)

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d0: ServiceDefinitionDict) -> "ServiceDefinition":
        image = d0.get("image", None)
        environment = d0.get("environment", {})
        if environment is None:
            environment = {}

        build = d0.get("build", None)
        if build is not None:
            build = Build.from_yaml(build)

        if build and image:
            msg = 'Cannot specify both "build" and "image".'
            raise ValueError(msg)

        # image_digest = d0.get("image_digest", None)
        # if image_digest:
        #     image = f"{image}@{image_digest}"

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
        ports_ = d0.get("ports", [])
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


class EvaluationParametersDict(TypedDict):
    """Extremely similar to docker-compose"""

    version: str
    services: Dict[str, ServiceDefinitionDict]
    # "/scenario"


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
    services: Dict[ServiceName, ServiceDefinition]

    def __init__(self, version, services):
        self.version = version
        self.services = services

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d0: EvaluationParametersDict) -> "EvaluationParameters":
        d = dict(d0)
        services_ = d.pop("services")
        if not isinstance(services_, dict):
            msg = "Expected dict"
            raise ZValueError(msg, got=services_)

        if not services_:
            msg = "No services described."
            raise ZValueError(msg)

        version = d.pop("version", "3")
        if d:
            msg = "Extra field in the configuration"
            raise ZValueError(msg, d0=d0, extra=list(d))
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

    def equivalent(self, other: "EvaluationParameters"):
        if set(other.services) != set(self.services):
            msg = "Different set of services."
            raise NotEquivalent(msg)
        for s in other.services:
            mine = self.services[s]
            its = other.services[s]
            try:
                mine.equivalent(its)
            except NotEquivalent as e:
                msg = f"Service {s} differs"
                raise NotEquivalent(msg, mine=mine, its=its) from e


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
    def from_yaml(cls, data, name) -> "ChallengeStep":
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


class NotEquivalent(ZException):
    pass


def nice_repr(x):
    K = type(x).__name__
    return "%s\n\n%s" % (K, indent(safe_yaml_dump(x.as_dict()), "   "))


# Transition = namedtuple("Transition", "first condition second")


@dataclass
class SimpleCondition:
    step: StepName
    status: JobStatusString


@dataclass
class AndCondition:
    subs: "List[Condition]"


Condition = Union[SimpleCondition, AndCondition]
AndCondition.__annotations__["subs"] = List[Condition]


def describe(c: Condition) -> str:
    if isinstance(c, SimpleCondition):
        if c.step == STATE_START and c.status == ChallengesConstants.STATUS_JOB_SUCCESS:
            return "At the beginning"
        else:
            return f"step `{c.step}` has result {c.status}"
    elif isinstance(c, AndCondition):
        return " and ".join(f"({describe(sub)})" for sub in c.subs)
    else:
        raise ZNotImplementedError(c=c)


def get_all_steps_mentioned(c: Condition) -> Iterator[StepName]:
    if isinstance(c, SimpleCondition):
        yield c.step
    elif isinstance(c, AndCondition):
        for s in c.subs:
            yield from get_all_steps_mentioned(s)
    else:
        raise ZNotImplementedError(c=c)


#
# @dataclass
# class OrCondition:
#     subs: "List[Condition]"


@dataclass
class Transition:
    condition: Condition
    second: StepName


class InvalidSteps(ZException):
    pass


@dataclass(repr=False)
class ChallengeTransitions:
    steps: List[StepName]
    transitions: List[Transition]

    def as_list(self):
        res = []
        for transition in self.transitions:
            if isinstance(transition.condition, SimpleCondition):
                a = transition.condition.step
                b = transition.condition.status
            elif isinstance(transition.condition, AndCondition):
                st = set(_.status for _ in transition.condition.subs)
                if len(st) != 1:
                    raise ZNotImplementedError(transition=transition)
                a = ",".join(_.step for _ in transition.condition.subs)
                b = list(st)[0]
            else:
                raise ZNotImplementedError(transition=transition)
            res.append([a, b, transition.second])
        return res

    def __repr__(self):
        return "\n".join(self.steps_explanation())

    def steps_explanation(self):
        ts = []
        for t in self.transitions:
            if t.condition == SimpleCondition(STATE_START, ChallengesConstants.STATUS_JOB_SUCCESS):
                ts.append(f"At the beginning execute step `{t.second}`.")
            else:
                condition_s = describe(t.condition)
                if t.second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                    m = f"If {condition_s}, then declare the submission `{t.second}`."
                else:
                    m = f"If {condition_s}, then execute step `{t.second}`."
                ts.append(m)
        return ts

    def top_ordered(self):
        _G = self.get_graph()  # XXX
        return list(self.steps)

    def get_graph(self) -> DiGraph:
        G = DiGraph()
        for t in self.transitions:
            for s in get_all_steps_mentioned(t.condition):
                G.add_edge(s, t.second)
        return G

    def get_precs(self, x: StepName) -> List[StepName]:
        G = self.get_graph()
        res = list(ancestors(G, x))
        # print('precs of %s: %s' % (x, res))
        return res

    def get_next_steps(
        self, status: Dict[StepName, JobStatusString], step2age=None
    ) -> Tuple[bool, Optional[EvalStateString], List[StepName]]:
        """status is a dictionary from step name to status.

        It contains at the beginning

            START: success

        Returns:
             bool (complete)
             optional status:  ['error', 'failed', 'success']
             a list of steps to activate next

        """
        CS = ChallengesConstants
        # logger.info('Received status = %s' % status)
        assert isinstance(status, dict)
        assert STATE_START in status
        # noinspection PyTypeChecker
        assert status[STATE_START] == CS.STATUS_JOB_SUCCESS
        status = dict(**status)
        for k, ks in list(status.items()):
            if k != STATE_START and k not in self.steps:
                # msg = "Ignoring invalid step %s -> %s" % (k, ks)
                # logger.error(msg)
                status.pop(k)

            if ks not in ChallengesConstants.ALLOWED_JOB_STATUS:
                # msg = f"Ignoring invalid step {k} -> {ks!r}"
                # logger.error(msg)
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

        def predecessors_success(_: StepName) -> bool:
            precs = self.get_precs(_)
            its_age = step2age.get(_, -1) if step2age else 0
            for k2 in precs:
                pred_age = step2age.get(k2, -1) if step2age else 0
                # logger.debug('%s %s %s %s' % (_, its_age, k2, pred_age))
                if pred_age > its_age:
                    # logger.debug('Its depedency is younger')
                    return False
                if k2 not in status or status[k2] != CS.STATUS_JOB_SUCCESS:
                    return False
            return True

        def is_condition_satisfied(c: Condition):
            if isinstance(c, SimpleCondition):
                return c.step in status and status[c.step] == c.status and predecessors_success(c.step)
            elif isinstance(c, AndCondition):
                return all(is_condition_satisfied(s) for s in c.subs)
            else:
                raise ZNotImplementedError(c=c)

        to_activate = cast(List[StepName], [])
        outcomes = set()
        for t in self.transitions:
            if is_condition_satisfied(t.condition):
                # logger.debug('Transition %s is activated' % str(t))

                like_it_does_not_exist = [ChallengesConstants.STATUS_JOB_ABORTED]
                if (
                    t.second in status
                    and status[t.second] not in like_it_does_not_exist
                    and predecessors_success(t.second)
                ):
                    # logger.debug('Second %s already activated (and in %s)' % (t.second, status[t.second]))
                    pass
                else:
                    if t.second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                        # logger.debug('Finishing here')
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

        # logger.debug('Incomplete; need to do: %s' % to_activate)
        return complete, outcome, to_activate


def steps_from_transitions(transitions: List[List[str]]) -> List[StepName]:
    steps = []
    for first, _, second in transitions:
        if first not in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
            firsts = ",".split(first)
            steps.extend(firsts)
        if second not in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
            steps.append(second)
    return steps


ListCondition = make_list(Condition)


def from_steps_transitions(steps: List[StepName], transitions_str: List[List[str]]) -> ChallengeTransitions:
    transitions = make_list(Transition)()
    for first_, condition, second in transitions_str:
        first_states = cast(List[StepName], first_.split(","))
        for _ in first_states:
            assert _ == STATE_START or _ in steps, (_, first_states)
        assert second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS] or second in steps, (second, steps)
        assert condition in ALLOWED_CONDITION_TRIGGERS, condition
        if len(first_states) == 1:
            c = SimpleCondition(first_states[0], condition)
        else:
            subs = [SimpleCondition(_, condition) for _ in first_states]
            c = AndCondition(ListCondition(subs))
        transitions.append(Transition(c, second))
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
            msg = "Invalid value"
            raise ZValueError(msg, order=self.order, allowed=Score.ALLOWED)

        if self.discretization is not None:
            discretization = float(self.discretization)
            if discretization <= 0:
                msg = "Need a strictly positive discretization"
                raise ZValueError(msg, discretization=discretization)

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
                name=name,
                description=description,
                order=order,
                discretization=discretization,
                short=short,
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
    name: ChallengeName
    title: str
    description: str
    protocol: str
    date_open: datetime
    date_close: datetime
    steps: Dict[StepName, ChallengeStep]
    transitions: List[List[str]]  # 3 elements each

    scoring: Scoring
    tags: List[str]

    dependencies: Dict[ChallengeName, ChallengeDependency]

    ct: ChallengeTransitions
    closure: Optional[List[ChallengeName]] = field(default_factory=list)

    def __post_init__(self):

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
        dependencies: Dict[ChallengeName, ChallengeDependency] = object_from_ipce(
            dependencies_, Dict[ChallengeName, ChallengeDependency]
        )
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
        data["transitions"] = self.ct.as_list()

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
    challenge_names: Optional[List[ChallengeName]]
    protocols: List[str]
    user_label: Optional[str]
    user_metadata: Dict[str, object]
    description: Optional[str]
    image: Optional[DockerCompleteImageName]  # optional docker image

    def __post_init_(self):
        if self.challenge_names is not None:
            if not isinstance(self.challenge_names, list):
                msg = f"Expected a list of strings for challenge names, got {self.challenge_names}"
                raise ValueError(msg)
        if not isinstance(self.protocols, list):
            msg = f"Expected a list of strings for protocols names, got {self.protocols}"
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
            image=self.image,
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
        image = data.pop("image", None)
        validation_challenge = data.pop("validation_challenge", None)

        return SubmissionDescription(
            challenge_names=challenges,
            protocols=protocols,
            description=description,
            user_label=user_label,
            user_metadata=user_metadata,
            image=image,
        )
