from collections import namedtuple
from datetime import datetime

import yaml
from contracts import raise_wrapped, check_isinstance

from duckietown_challenges import ChallengesConstants
from duckietown_challenges.utils import wrap_config_reader
from . import dclogger


class InvalidChallengeDescription(Exception):
    pass


STATE_START = 'START'
STATE_ERROR = 'ERROR'
STATE_SUCCESS = 'SUCCESS'
STATE_FAILED = 'FAILED'

ALLOWED_CONDITION_TRIGGERS = ChallengesConstants.ALLOWED_JOB_STATUS

allowed_permissions = ['snoop', 'change', 'moderate', 'grant']


class ChallengeStep(object):
    def __init__(self, name, title, description, evaluation_parameters,
                 features_required, timeout):
        self.name = name
        self.title = title
        self.description = description
        check_isinstance(evaluation_parameters, EvaluationParameters)
        self.evaluation_parameters = evaluation_parameters
        check_isinstance(features_required, dict)
        self.features_required = features_required
        self.timeout = timeout

    def as_dict(self):
        data = {}
        data['title'] = self.title
        data['description'] = self.description
        data['evaluation_parameters'] = self.evaluation_parameters.as_dict()
        data['features_required'] = self.features_required
        data['timeout'] = self.timeout
        return data

    @staticmethod
    @wrap_config_reader
    def from_yaml(data0, name):
        if not isinstance(data0, dict):
            msg = 'Need dict, got %s' % data0
            raise ValueError(msg)

        data = data0.copy()

        title = data.pop('title')
        description = data.pop('description')
        evaluation_parameters = EvaluationParameters.from_yaml(data.pop('evaluation_parameters'))
        features_required = data.pop('features_required')

        timeout = data.pop('timeout')

        if data:
            msg = 'Extra fields: %s' % list(data)
            raise ValueError(msg)

        return ChallengeStep(name, title, description, evaluation_parameters,
                             features_required, timeout=timeout)

    def update_image(self):
        self.evaluation_parameters.update_image()

SUBMISSION_CONTAINER_TAG = 'SUBMISSION_CONTAINER'

class EvaluationParameters(object):
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

    def __init__(self, version, services):
        self.version = version
        self.services = services

    @staticmethod
    @wrap_config_reader
    def from_yaml(d0):
        if not isinstance(d0, dict):
            msg = 'Expected dict, got %s' % d0.__repr__()
            raise ValueError(msg)
        d = dict(**d0)
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

        if d:
            msg = 'Invalid fields %s' % list(d)
            raise ValueError(msg)

        # check that there is at least a service with the image called
        # SUBMISSION_CONTAINER
        n = 0
        for service_definition in services.values():
            if service_definition.image == SUBMISSION_CONTAINER_TAG:
              n += 1
        if n == 0:
            msg = 'I expect one of the services to have "image: %s".' % SUBMISSION_CONTAINER_TAG
            raise ValueError(msg)
        if n>1:
            msg = 'Too many services with  "image: %s".' % SUBMISSION_CONTAINER_TAG
            raise ValueError(msg)

        return EvaluationParameters(services=services, version=version)

    def as_dict(self):
        services = dict([(k, v.as_dict()) for k, v in self.services.items()])
        return dict(version=self.version, services=services)


class ServiceDefinition(object):
    def __init__(self, image, environment):
        check_isinstance(environment, dict)
        check_isinstance(image, (unicode, str))
        self.image = str(image)
        self.environment = environment

    def update_image(self):
        self.image = get_latest(self.image)

    @staticmethod
    @wrap_config_reader
    def from_yaml(d0):
        if not isinstance(d0, dict):
            msg = 'Expected dict, got %s' % d0.__repr__()
            raise ValueError(msg)
        d = dict(**d0)
        if 'image' in d:
            image = d.pop('image')
        elif 'container' in d:
            image = d.pop('container')
        else:
            msg = 'Need parameter "image": %s' % d0
            raise ValueError(msg)
        environment = d.pop('environment', {})
        if environment is None:
            environment = {}

        if d:
            msg = 'Extra fields: %s' % d0
            raise ValueError(msg)
        return ServiceDefinition(image, environment)

    def as_dict(self):
        return dict(image=self.image, environment=self.environment)


def get_latest(image_name):
    if '@' in image_name:
        msg = 'The image %r already has a qualified hash. Not updating.' % image_name
        dclogger.warning(msg)
        return
    import docker
    client = docker.from_env()
    dclogger.info('Finding latest version of %s' % image_name)
    image = client.images.get(image_name)
    if ':' in image_name:
        # remove tag
        image_name_no_tag = image_name[:image_name.index(':')]
        image_name = image_name_no_tag

    fq = image_name + '@' + image.id
    dclogger.info('updated %s -> %r' % (image_name, fq))
    return fq


Transition = namedtuple('Transition', 'first condition second')


class InvalidSteps(Exception):
    pass


class ChallengeTransitions(object):
    def __init__(self, transitions, steps):
        self.transitions = []
        self.steps = steps
        for first, condition, second in transitions:
            assert first == STATE_START or first in self.steps, first
            assert second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS] or second in self.steps, second
            assert condition in ALLOWED_CONDITION_TRIGGERS, condition
            self.transitions.append(Transition(first, condition, second))

    def get_next_steps(self, status):
        """ status is a dictionary from step ID to
            status.

            It contains at the beginning

                START: success

            Returns a list of steps.

            If the list is empty, then we are done

        """
        dclogger.info('Received status = %s' % status)
        assert isinstance(status, dict)
        assert STATE_START in status
        assert status[STATE_START] == 'success'
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

        to_activate = []
        for t in self.transitions:
            if t.first in status and status[t.first] == t.condition:
                dclogger.debug('Transition %s is activated' % str(t))

                like_it_does_not_exist = [ChallengesConstants.STATUS_ABORTED]
                if t.second in status and status[t.second] not in like_it_does_not_exist:
                    dclogger.debug('Second %s already activated (and in %s)' % (t.second, status[t.second]))
                else:
                    if t.second in [STATE_ERROR, STATE_FAILED, STATE_SUCCESS]:
                        dclogger.debug('Finishing here')
                        return True, t.second.lower(), []
                    else:

                        to_activate.append(t.second)

        dclogger.debug('Incomplete; need to do: %s' % to_activate)
        return False, None, to_activate


class ChallengeDescription(object):
    def __init__(self, name, title, description, protocol,
                 date_open, date_close, steps, roles, transitions):
        self.name = name
        self.title = title
        self.description = description
        self.protocol = protocol
        self.date_open = date_open
        check_isinstance(date_open, datetime)
        check_isinstance(date_close, datetime)
        self.date_close = date_close
        self.steps = steps
        self.roles = roles

        for k, permissions in self.roles.items():
            if not k.startswith('user:'):
                msg = 'Permissions should start with "user:", %s' % k
                raise InvalidChallengeDescription(msg)
            p2 = dict(**permissions)
            for perm in allowed_permissions:
                p2.pop(perm, None)
            if p2:
                msg = 'Unknown permissions: %s' % p2
                raise InvalidChallengeDescription(msg)

        self.first_step = None
        self.ct = ChallengeTransitions(transitions, list(self.steps))

    def get_steps(self):
        return self.steps

    def get_next_steps(self, status):
        return self.ct.get_next_steps(status)

    @staticmethod
    @wrap_config_reader
    def from_yaml(data):
        try:
            name = data['challenge']
            title = data['title']
            description = data['description']
            protocol = data['protocol']
            date_open = data['date-open']
            date_close = data['date-close']

            roles = data['roles']
            transitions = data['transitions']
            steps = data['steps']
            Steps = {}
            for k, v in steps.items():
                Steps[k] = ChallengeStep.from_yaml(v, k)

            return ChallengeDescription(name, title, description,
                                        protocol, date_open, date_close, Steps,
                                        roles=roles, transitions=transitions)
        except KeyError as e:
            msg = 'Missing config %s' % e
            raise_wrapped(InvalidChallengeDescription, e, msg)

    def as_dict(self):
        data = {}
        data['challenge'] = self.name
        data['title'] = self.title
        data['description'] = self.description
        data['protocol'] = self.protocol
        data['date-open'] = self.date_open
        data['date-close'] = self.date_close
        data['roles'] = self.roles
        data['transitions'] = []
        for t in self.ct.transitions:
            tt = [t.first, t.condition, t.second]
            data['transitions'].append(tt)
        data['steps'] = {}
        for k, v in self.steps.items():
            data['steps'][k] = v.as_dict()
        return data

    def as_yaml(self):
        return yaml.dump(self.as_dict())
