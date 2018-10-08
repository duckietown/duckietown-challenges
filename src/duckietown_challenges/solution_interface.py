from abc import ABCMeta, abstractmethod


class ChallengeInterfaceEvaluator(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_current_step(self):
        """ Returns the current step. """

    @abstractmethod
    def get_completed_steps(self):
        """ Returns the previous steps as a list of string """

    @abstractmethod
    def get_completed_step_evaluation_files(self, step_name):
        """ Returns a list of names for the files completed in a previous step. """

    @abstractmethod
    def get_completed_step_evaluation_file(self, step_name, basename):
        """ Returns a filename for one of the files completed in a previous step."""

    def get_completed_step_evaluation_file_contents(self, step_name, basename):
        fn = self.get_completed_step_evaluation_file(step_name, basename)
        with open(fn) as f:
            return f.read()

    @abstractmethod
    def set_challenge_parameters(self, data):
        pass

    @abstractmethod
    def get_tmp_dir(self):
        pass

    # preparation

    @abstractmethod
    def set_challenge_file(self, basename, from_file, description=None):
        pass

    # evaluation

    @abstractmethod
    def get_solution_output_dict(self):
        pass

    @abstractmethod
    def get_solution_output_file(self, basename):
        pass

    @abstractmethod
    def get_solution_output_files(self):
        pass

    @abstractmethod
    def set_score(self, name, value, description=None):
        pass

    @abstractmethod
    def set_evaluation_file(self, basename, from_file, description=None):
        pass

    @abstractmethod
    def set_evaluation_file_from_data(self, basename, contents, description=None):
        pass

    @abstractmethod
    def info(self, s):
        pass

    @abstractmethod
    def error(self, s):
        pass

    @abstractmethod
    def debug(self, s):
        pass


class ChallengeInterfaceSolution(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_tmp_dir(self):
        pass

    @abstractmethod
    def get_challenge_parameters(self):
        pass

    @abstractmethod
    def get_challenge_file(self, basename):
        pass

    @abstractmethod
    def get_challenge_files(self):
        pass

    @abstractmethod
    def set_solution_output_dict(self, data):
        pass

    @abstractmethod
    def declare_failure(self, msg):
        pass

    @abstractmethod
    def set_solution_output_file(self, basename, from_file, description=None):
        pass

    @abstractmethod
    def set_solution_output_file_from_data(self, basename, contents, description=None):
        pass

    @abstractmethod
    def info(self, s):
        pass

    @abstractmethod
    def error(self, s):
        pass

    @abstractmethod
    def debug(self, s):
        pass

    @abstractmethod
    def get_current_step(self):
        """ Returns the current step. """

    @abstractmethod
    def get_completed_steps(self):
        """ Returns the previous steps as a list of string """

    @abstractmethod
    def get_completed_step_solution_files(self, step_name):
        """ Returns a list of names for the files completed in a previous step. """

    @abstractmethod
    def get_completed_step_solution_file(self, step_name, basename):
        """ Returns a filename for one of the files completed in a previous step."""

    def get_completed_step_solution_file_contents(self, step_name, basename):
        fn = self.get_completed_step_solution_file(step_name, basename)
        with open(fn) as f:
            return f.read()


def check_valid_basename():
    pass  # TODO
