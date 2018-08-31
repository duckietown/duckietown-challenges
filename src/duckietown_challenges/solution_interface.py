from abc import ABCMeta, abstractmethod


class ChallengeInterfaceEvaluator(object):
    __metaclass__ = ABCMeta

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
    def set_evaluation_file(self, basename, from_file, description):
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
    def declare_failure(self, data):
        pass

    @abstractmethod
    def set_solution_output_file(self, basename, from_file, description):
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


def check_valid_basename():
    pass  # TODO
