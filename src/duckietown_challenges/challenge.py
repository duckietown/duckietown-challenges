from collections import namedtuple

import yaml
from contracts import raise_wrapped, check_isinstance
from duckietown_challenges import ChallengesConstants
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
                 features_required):
        self.name = name
        self.title = title
        self.description = description
        check_isinstance(evaluation_parameters, dict)
        self.evaluation_parameters = evaluation_parameters
        check_isinstance(features_required, dict)
        self.features_required = features_required

    def as_dict(self):
        data = {}
        data['title'] = self.title
        data['description'] = self.description
        data['evaluation_parameters'] = self.evaluation_parameters
        data['features_required'] = self.features_required
        return data

    @staticmethod
    def from_yaml(name, data):
        title = data['title']
        description = data['description']
        evaluation_parameters = data['evaluation_parameters']
        features_required = data['features_required']

        return ChallengeStep(name, title, description, evaluation_parameters,
                             features_required)


Transition = namedtuple('Transition', 'first condition second')
from datetime import datetime


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
                Steps[k] = ChallengeStep.from_yaml(name, v)

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



