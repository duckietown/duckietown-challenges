import os
from abc import abstractmethod, ABCMeta

import json
import yaml

from duckietown_challenges import CONFIG_LOCATION, OUTPUT_JSON


class ChallengeException(Exception):
    pass


class NotAvailable(ChallengeException):
    pass


class InvalidConfiguration(ChallengeException):
    pass


class ChallengeInterface(object):
    """
        This is the interface that is available to the challenge solution.
        It allows to know which directories to use for input and output, etc.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def declare_success(self, data):
        """ Declares success and writes the output data for challenges that have a JSON file as an output. """

    @abstractmethod
    def declare_failure(self, error_msg):
        """ Declares failure with the given error message.
            Writes the output data for challenges that have a JSON file as an output. """

    @abstractmethod
    def get_input_dir(self):
        """ Gets the directory for the input.

            Raises NotAvailable if not available.
        """

    @abstractmethod
    def get_output_dir(self):
        """ Gets the directory for the output. This is saved
            as a container and available for the previous step.
        """

    @abstractmethod
    def get_temp_dir(self):
        """ Gets the directory for writing temporary file. This is erased
            after the run. """

    @abstractmethod
    def get_previous_step_dir(self):
        """
            In case this is a multi-step challenge, returns the location
            of the output data for the previous step.

            Raises NotAvailable if not available.
        """

    def write_environment_info(self):
        try:
            print('input dir: %s' % self.get_input_dir())
        except NotAvailable:
            print('input dir: not available')
        print('output dir: %s' % self.get_output_dir())
        print('temp dir: %s' % self.get_temp_dir())
        try:
            print('last_step dir: %s' % self.get_previous_step_dir())
        except NotAvailable:
            print('last_step dir: not available')


def get_challenge_interface():
    """
        Gets the ChallengeInterface to use.

        Raises InvalidConfiguration if some of the configuration is missing or invalid.
    """
    return ConcreteChallengeInterface(CONFIG_LOCATION)


class ConcreteChallengeInterface(ChallengeInterface):

    def __init__(self, filename):

        data = yaml.load(open(filename).read())

        try:
            self.input_dir = data.get('input_dir')
            self.previous_step_dir = data.get('previous_step_dir')
            self.output_dir = data.get('output_dir')
            self.temp_dir = data.get('temp_dir')
        except KeyError as e:
            msg = 'Missing configuration option: %s.' % e
            raise InvalidConfiguration(msg)

        if self.input_dir:
            if not os.path.exists(self.input_dir):
                msg = 'Invalid input dir: %s' % self.input_dir
                raise InvalidConfiguration(msg)

        if self.previous_step_dir:
            if not os.path.exists(self.previous_step_dir):
                msg = 'Invalid previous_step_dir dir: %s' % self.previous_step_dir
                raise InvalidConfiguration(msg)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def declare_success(self, data):
        res = json.dumps(data)
        data['ok'] = True
        fn = os.path.join(self.output_dir, OUTPUT_JSON)
        with open(fn, 'w') as f:
            f.write(res)

    def declare_failure(self, data):
        data['ok'] = False
        res = json.dumps(data)
        fn = os.path.join(self.output_dir, OUTPUT_JSON)
        with open(fn, 'w') as f:
            f.write(res)

    def get_input_dir(self):
        if not self.input_dir:
            msg = 'There is no input dir defined.'
            raise NotAvailable(msg)
        return self.input_dir

    def get_output_dir(self):
        return self.output_dir

    def get_temp_dir(self):
        return self.temp_dir

    def get_previous_step_dir(self):
        if not self.previous_step_dir:
            msg = 'No temporary dir is defined.'
            raise NotAvailable(msg)
        return self.previous_step_dir
