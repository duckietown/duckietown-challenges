# coding=utf-8
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, date
from typing import *

import yaml
from networkx import DiGraph, ancestors

from . import dclogger
from .challenges_constants import ChallengesConstants
from .cmd_submit_build import parse_complete_tag
from .exceptions import InvalidConfiguration
from .utils import indent, safe_yaml_dump, check_isinstance, wrap_config_reader2


class InvalidChallengeDescription(Exception):
    pass


# these are job statuses
STATE_START = 'START'
STATE_ERROR = 'ERROR'
STATE_SUCCESS = 'SUCCESS'
STATE_FAILED = 'FAILED'

ALLOWED_CONDITION_TRIGGERS = ChallengesConstants.ALLOWED_JOB_STATUS

# allowed_permissions = ['snoop', 'change', 'moderate', 'grant']


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
            msg = 'Expected dict, got %s' % d0.__repr__()
            raise ValueError(msg)
        d = dict(**d0)

        context = d.pop('context', '.')
        dockerfile = d.pop('dockerfile', 'Dockerfile')
        args = d.pop('args', {})

        if d:
            msg = 'Extra fields: %s' % list(d0)
            raise ValueError(msg)
        return Build(context, dockerfile, args)


@dataclass
class PortDefinition:
    external: int
    internal: int


@dataclass
class ServiceDefinition:
    image: Optional[str]
    build: Build
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
                msg = 'Could not even parse mine'
                raise NotEquivalent(msg) from e

            if br1.digest is None or br2.digest is None:
                msg = 'No digest information, assuming different.\nself: %s\nother: %s' % (br1, br2)
                raise NotEquivalent(msg)
            if br1.digest != br2.digest:
                msg = 'Different digests:\n\n  %s\n\n  %s' % (br1, br2)
                raise NotEquivalent(msg)
            if self.ports != other.ports:
                msg = 'Different digests:\n\n  %s\n\n  %s' % (br1, br2)
                raise NotEquivalent(msg)

        if self.environment != other.environment:
            msg = 'Different environments:\n\n %s\n\n  %s' % (self.environment, other.environment)
            raise NotEquivalent(msg)

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d0):
        image = d0.pop('image', None)
        environment = d0.pop('environment', {})
        if environment is None:
            environment = {}

        if 'build' in d0:
            build = d0.pop('build')
            if build is not None:
                build = Build.from_yaml(build)
        else:
            build = None

        if build and image:
            msg = 'Cannot specify both "build" and "image".'
            raise ValueError(msg)

        image_digest = d0.pop('image_digest', None)
        if image_digest:
            image = f'{image}@{image_digest}'

        for k, v in list(environment.items()):
            if '-' in k:
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
                msg = 'The type %s is not allowed for environment variable "%s".' % (type(v).__name__, k)
                raise InvalidConfiguration(msg)
        ports_ = d0.pop('ports', [])
        ports = []
        for s in ports_:
            if not ':' in s:
                raise InvalidConfiguration(s)
            tokens = s.split(':')
            external = int(tokens[0])
            internal = int(tokens[1])
            ports.append(PortDefinition(external=external, internal=internal))
        return ServiceDefinition(image=image, environment=environment, build=build, ports=ports)

    def as_dict(self):

        res = dict(image=self.image, environment=self.environment)

        ports = []
        for p in self.ports:
            ports.append('%s:%s' % (p.external, p.internal))

        if ports:
            res['ports'] = ports
        if self.build:
            res['build'] = self.build.as_dict()
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

        services_ = d.pop('services')
        if not isinstance(services_, dict):
            msg = 'Expected dict got %s' % services_.__repr__()
            raise ValueError(msg)

        if not services_:
            msg = 'No services described.'
            raise ValueError(msg)

        version = d.pop('version', '3')

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
            msg = 'Different set of services.'
            raise NotEquivalent(msg)
        for s in other.services:
            try:
                self.services[s].equivalent(other.services[s])
            except NotEquivalent as e:
                msg = 'Service %r differs:\n\n%s' % (s, indent(e, '  '))
                raise NotEquivalent(msg)


@dataclass
class ChallengeStep:
    name: str
    title: str
    description: str
    evaluation_parameters: EvaluationParameters
    features_required: Dict[str, Any]
    timeout: float
    uptodate_token: Optional[str] = None

    def as_dict(self):
        data = {}
        data['title'] = self.title
        data['description'] = self.description
        data['evaluation_parameters'] = self.evaluation_parameters.as_dict()
        data['features_required'] = self.features_required
        data['timeout'] = self.timeout
        data['uptodate_token'] = self.uptodate_token
        return data

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, data, name):
        title = data.pop('title')
        description = data.pop('description')
        evaluation_parameters = EvaluationParameters.from_yaml(data.pop('evaluation_parameters'))
        features_required = data.pop('features_required', {})
        timeout = data.pop('timeout')
        uptodate_token = data.pop('uptodate_token', None)
        return ChallengeStep(name, title, description, evaluation_parameters,
                             features_required, timeout=timeout, uptodate_token=uptodate_token)


class NotEquivalent(Exception):
    pass


def nice_repr(x):
    K = type(x).__name__
    return '%s\n\n%s' % (K, indent(safe_yaml_dump(x.as_dict()), '   '))


Transition = namedtuple('Transition', 'first condition second')


class InvalidSteps(Exception):
    pass


@dataclass(repr=False)
class ChallengeTransitions:
    steps: List[str]
    transitions: List[Transition]

    @staticmethod
    def steps_from_transitions(transitions):
        steps = set()
        for first, condition, second in transitions:
            if first not in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                steps.add(first)
            if second not in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                steps.add(second)

        return steps

    @staticmethod
    def from_steps_transitions(steps: List[str], transitions_str: List[List[str]]):
        transitions = []
        for first, condition, second in transitions_str:
            assert first == STATE_START or first in steps, first
            assert second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS] or second in steps, second
            assert condition in ALLOWED_CONDITION_TRIGGERS, condition
            transitions.append(Transition(first, condition, second))
        return ChallengeTransitions(steps, transitions)

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
        return u"\n".join(self.steps_explanation())

    def steps_explanation(self):
        ts = []
        for first, condition, second in self.transitions:
            if first == STATE_START:
                ts.append('At the beginning execute step `%s`.' % second)
            else:
                if second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                    ts.append('If step `%s` finishes with status `%s`, then declare the submission `%s`.' %
                              (first, condition, second))
                else:
                    ts.append('If step `%s` finishes with status `%s`, then execute step `%s`.' %
                              (first, condition, second))
        return ts

    def top_ordered(self):
        _G = self.get_graph()  # XXX
        return list(self.steps)

    def get_graph(self):
        G = DiGraph()
        for first, condition, second in self.transitions:
            G.add_edge(first, second)
        return G

    def get_precs(self, x):
        G = self.get_graph()
        res = list(ancestors(G, x))
        # print('precs of %s: %s' % (x, res))
        return res

    def get_next_steps(self, status: Dict[str, str],
                       step2age=None) -> Tuple[bool, Optional[str], List[str]]:
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
                msg = 'Ignoring invalid step %s -> %s' % (k, ks)
                dclogger.error(msg)
                status.pop(k)
            if ks not in ChallengesConstants.ALLOWED_JOB_STATUS:
                msg = 'Ignoring invalid step %s -> %s' % (k, ks)
                dclogger.error(msg)
                status.pop(k)

            # timeout or aborted or host error = like it never happened
            if ks in [CS.STATUS_JOB_TIMEOUT, CS.STATUS_JOB_ABORTED, CS.STATUS_JOB_HOST_ERROR]:
                status.pop(k)

        # make sure that the steps in which they depend are ok

        def predecessors_success(_):
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

        to_activate = []
        for t in self.transitions:
            if t.first in status and status[t.first] == t.condition and predecessors_success(t.first):
                # dclogger.debug('Transition %s is activated' % str(t))

                like_it_does_not_exist = [ChallengesConstants.STATUS_JOB_ABORTED]
                if t.second in status and status[t.second] not in like_it_does_not_exist and \
                        predecessors_success(t.second):
                    # dclogger.debug('Second %s already activated (and in %s)' % (t.second, status[t.second]))
                    pass
                else:
                    if t.second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                        # dclogger.debug('Finishing here')
                        return True, t.second.lower(), []
                    else:

                        to_activate.append(t.second)

        # dclogger.debug('Incomplete; need to do: %s' % to_activate)
        return False, None, to_activate


class Score:
    HIGHER_IS_BETTER = 'higher-is-better'
    LOWER_IS_BETTER = 'lower-is-better'
    ALLOWED = [HIGHER_IS_BETTER, LOWER_IS_BETTER]

    def __init__(self, name, description, order, discretization, short):
        if description == 'descending':
            order = Score.HIGHER_IS_BETTER

        if description == 'ascending':
            order = Score.LOWER_IS_BETTER

        if order not in Score.ALLOWED:
            msg = 'Invalid value %s' % order
            raise ValueError(msg)

        if discretization is not None:
            discretization = float(discretization)
            if discretization <= 0:
                msg = 'Need a strictly positive discretization: %s' % discretization
                raise ValueError(msg)
        self.name = name
        self.description = description
        self.order = order
        self.discretization = discretization
        self.short = short

    def __repr__(self):
        return nice_repr(self)

    def as_dict(self):
        return dict(description=self.description, name=self.name, order=self.order,
                    discretization=self.discretization, short=self.short)

    @classmethod
    def from_yaml(cls, data0):
        try:
            if not isinstance(data0, dict):
                msg = 'Expected dict, got %s' % type(data0).__name__
                raise InvalidChallengeDescription(msg)

            data = dict(**data0)
            short = data.pop('short', None)
            name = data.pop('name')
            description = data.pop('description', None)
            order = data.pop('order', Score.HIGHER_IS_BETTER)
            # TODO: remove
            if order == 'ascending':
                order = Score.HIGHER_IS_BETTER
            if order == 'descending':
                order = Score.LOWER_IS_BETTER
            if order not in Score.ALLOWED:
                msg = 'Invalid value "%s" not in %s.' % (order, Score.ALLOWED)
                raise InvalidChallengeDescription(msg)

            discretization = data.pop('discretization', None)

            if data:
                msg = 'Extra keys in configuration file: %s' % list(data)
                raise InvalidChallengeDescription(msg)

            return Score(name=name, description=description, order=order, discretization=discretization, short=short)
        except KeyError as e:
            msg = 'Missing config %s' % e
            raise InvalidChallengeDescription(msg) from e


@dataclass(repr=False)
class Scoring:
    scores: List[Score]

    def as_dict(self):
        scores = [_.as_dict() for _ in self.scores]
        return dict(scores=scores)

    def __repr__(self):
        return nice_repr(self)

    @classmethod
    def from_yaml(cls, data0):
        try:
            if not isinstance(data0, dict):
                msg = 'Expected dict, got %s' % type(data0).__name__
                raise InvalidChallengeDescription(msg)

            data = dict(**data0)
            scores = data.pop('scores')
            if not isinstance(scores, list):
                msg = 'Expected list, got %s' % type(scores).__name__
                raise InvalidChallengeDescription(msg)

            scores = [Score.from_yaml(_) for _ in scores]
            if data:
                msg = 'Extra keys in configuration file: %s' % list(data)
                raise InvalidChallengeDescription(msg)

            return Scoring(scores)

        except KeyError as e:
            msg = 'Missing config %s' % e
            raise InvalidChallengeDescription(msg) from e


class ChallengeDescription:
    name: str
    title: str
    description: str
    protocol: str
    date_open: datetime
    date_close: datetime
    steps: Dict[str, ChallengeStep]
    # roles: Any
    ct: ChallengeTransitions
    scoring: Scoring

    def __init__(self, name, title, description, protocol,
                 date_open, date_close, steps, transitions, tags, scoring):
        self.name = name
        self.title = title
        self.scoring = scoring
        self.description = description
        self.protocol = protocol
        self.date_open = date_open
        check_isinstance(date_open, datetime)
        check_isinstance(date_close, datetime)
        self.date_close = date_close
        self.steps = steps
        # self.roles = roles
        self.tags = tags

        # for k, permissions in self.roles.items():
        #     if not k.startswith('user:'):
        #         msg = 'Permissions should start with "user:", %s' % k
        #         raise InvalidChallengeDescription(msg)
        #     p2 = dict(**permissions)
        #     for perm in allowed_permissions:
        #         p2.pop(perm, None)
        #     if p2:
        #         msg = 'Unknown permissions: %s' % p2
        #         raise InvalidChallengeDescription(msg)

        self.first_step = None
        self.ct = ChallengeTransitions.from_steps_transitions(list(self.steps), transitions)

    def get_steps(self):
        return self.steps

    def get_next_steps(self, status):
        return self.ct.get_next_steps(status)

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, data):
        name = data.pop('challenge')
        tags = data.pop('tags', [])
        title = data.pop('title')
        description = data.pop('description')
        protocol = data.pop('protocol')
        date_open = interpret_date(data.pop('date-open'))
        date_close = interpret_date(data.pop('date-close'))

        data.pop('roles', None)

        steps = data.pop('steps')
        Steps = {}
        for k, v in steps.items():
            Steps[k] = ChallengeStep.from_yaml(v, k)

        transitions = data.pop('transitions', None)
        if transitions is None:
            if len(Steps) == 1:
                stepname = list(Steps)[0]
                transitions = [
                    ['START', 'success', stepname, ],
                    [stepname, 'success', 'SUCCESS'],
                    [stepname, 'failed', 'FAILED'],
                    [stepname, 'error', 'ERROR'],
                ]
            else:
                msg = 'Need transitions if there is more than one step.'
                raise ValueError(msg)

        scoring = Scoring.from_yaml(data.pop('scoring'))

        return ChallengeDescription(name, title, description,
                                    protocol, date_open, date_close, Steps,
                                    transitions=transitions,
                                    tags=tags, scoring=scoring)

    def as_dict(self):
        data = {}
        data['challenge'] = self.name
        data['title'] = self.title
        data['description'] = self.description
        data['protocol'] = self.protocol
        data['date-open'] = self.date_open.isoformat() if self.date_open else None
        data['date-close'] = self.date_close.isoformat() if self.date_close else None
        # data['roles'] = self.roles
        data['transitions'] = []
        for t in self.ct.transitions:
            tt = [t.first, t.condition, t.second]
            data['transitions'].append(tt)
        steps = {}
        for k, v in self.steps.items():
            steps[k] = v.as_dict()
        data['steps'] = steps

        data['tags'] = self.tags
        data['scoring'] = self.scoring.as_dict()
        return data

    def as_yaml(self):
        return yaml.dump(self.as_dict())

    def __repr__(self):
        return nice_repr(self)


def interpret_date(d):
    if d is None:
        return d
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime.combine(d, datetime.min.time())

    if isinstance(d, str):
        from dateutil import parser
        return parser.parse(d)
    raise ValueError(d.__repr__())


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
                msg = 'Expected a list of strings for challenge names, got %s' % self.challenge_names
                raise ValueError(msg)
        if not isinstance(self.protocols, list):
            msg = 'Expected a list of strings for protocols names, got %s' % self.protocols
            raise ValueError(msg)

    def __repr__(self):
        return nice_repr(self)

    def as_dict(self):
        return dict(protocols=self.protocols,
                    challenge_names=self.challenge_names,
                    user_label=self.user_label,
                    user_metadata=self.user_metadata,
                    description=self.description)

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, data):
        challenge_name = data.pop('challenge', None)
        if challenge_name is None:
            challenges = None
        else:
            if isinstance(challenge_name, list):
                challenges = challenge_name
            else:
                challenges = [challenge_name]

        protocol = data.pop('protocol')
        if isinstance(protocol, list):
            protocols = protocol
        else:
            protocols = [protocol]

        description = data.pop('description', None)
        user_label = data.pop('user-label', None)
        user_metadata = data.pop('user-payload', None)

        return SubmissionDescription(challenge_names=challenges,
                                     protocols=protocols,
                                     description=description,
                                     user_label=user_label,
                                     user_metadata=user_metadata)
