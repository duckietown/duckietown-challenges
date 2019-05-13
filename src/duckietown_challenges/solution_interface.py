# coding=utf-8
from abc import ABCMeta, abstractmethod


class ChallengeInterfaceSolution(metaclass=ABCMeta):
    """
      When a solution runs, an instance of this class
      is passed to the solution's run() method.

    """

    # Misc methods for accessing the environment
    @abstractmethod
    def get_tmp_dir(self):
        """ Get a temporary directory in which to work. """

    # Logging methods

    @abstractmethod
    def info(self, s):
        """ Writes a log message. """

    @abstractmethod
    def error(self, s):
        """ Writes an error message. """

    @abstractmethod
    def debug(self, s):
        """ Writes a debug message. """

    # Get challenge information from the evaluator

    @abstractmethod
    def get_challenge_parameters(self):
        """
            Returns a dict created by the evaluator.

            :return: a dictionary
        """

    @abstractmethod
    def get_challenge_file(self, basename):
        """
            Gets a file passed by the evaluator.

            :return: Returns a filename (read-only).

        """

    @abstractmethod
    def get_challenge_files(self):
        """
            Returns a list of basenames available for reading
            through get_challenge_file().

            :return: a list of strings

        """

    # Status methods

    @abstractmethod
    def set_solution_output_dict(self, data):
        """
            This method's invocation means that the solution
            finished succesfully (in its own view).

            :param data: a dictionary that will be passed to the evaluator.
            :return: None
        """

    @abstractmethod
    def declare_failure(self, msg):
        """
            Calling this method means that the solution has given up.

            :param msg: An error message that will be available to the user.
            :return: None
        """

    # Artefacts methods - saving files

    @abstractmethod
    def set_solution_output_file(self, basename: str, from_file: str, description=None):
        """
            Creates an artefact called "basename" from the file `from_file`.

            :param basename: Name that can be used later to refer to the file.
            :param from_file: Path to read.
            :param description: Optional description of the artefact.
            :return: None
        """

    @abstractmethod
    def set_solution_output_file_from_data(self, basename: str, contents: bytes, description=None):
        """
            Same as before, but the contents is passed as a string.

            :param basename: Name that can be used later to refer to the file.
            :param contents: Contents of the file.
            :param description: Optional description of the artefact.
            :return: None
        """

    # Multi-step-API

    @abstractmethod
    def get_current_step(self):
        """
            Returns the name of the current step.

            :return: a string
        """

    @abstractmethod
    def get_completed_steps(self):
        """
            Returns the previous steps as a list of string.

            :return: a list of strings
        """

    @abstractmethod
    def get_completed_step_solution_files(self, step_name: str):
        """

            Returns a list of names for the files completed in a previous step.

            :param step_name: Name of previous step.
            :return: a list of strings

        """

    @abstractmethod
    def get_completed_step_solution_file(self, step_name: str, basename: str):
        """

            Returns a filename for one of the files completed in a previous step.

            :param step_name: Name of previous step.
            :param basename: Name used in `set_solution_output_file()`.
            :return: a path to a read-only file.

        """

    def get_completed_step_solution_file_contents(self, step_name: str, basename: str) -> bytes:
        """
            Same as `get_completed_step_solution_file` but returns the contents
            directly.

            :param step_name: Name of previous step.
            :param basename: Name used in `set_solution_output_file()`.
            :return: a string with the contents of the file.

        """
        fn = self.get_completed_step_solution_file(step_name, basename)
        with open(fn, 'rb') as f:
            return f.read()


class ChallengeInterfaceEvaluator(metaclass=ABCMeta):


    # Methods for the

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

    def get_completed_step_evaluation_file_contents(self, step_name, basename) -> bytes:
        fn = self.get_completed_step_evaluation_file(step_name, basename)
        with open(fn, 'rb') as f:
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

    def set_scores(self, d):
        for k, v in d.items():
            self.set_score(k, v)

    @abstractmethod
    def set_evaluation_file(self, basename, from_file, description=None):
        pass

    def set_evaluation_dir(self, basename, realdir):
        import os
        for bn in os.listdir(realdir):
            fn = os.path.join(realdir, bn)
            if os.path.isdir(fn):
                self.set_evaluation_dir(os.path.join(basename, bn), fn)
            else:
                self.set_evaluation_file(os.path.join(basename, bn), fn)

    @abstractmethod
    def set_evaluation_ipfs_hash(self, rpath: str, cid: str):
        pass

    @abstractmethod
    def set_evaluation_file_from_data(self, basename, contents: bytes, description=None):
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
