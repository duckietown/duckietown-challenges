import sys
import traceback
from abc import ABCMeta, abstractmethod

from contracts import indent


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


#
#
# class ChallengeInterface(object):
#     """
#         This is the interface that is available to the challenge solution.
#         It allows to know which directories to use for input and output, etc.
#     """
#
#     def get_output_dir(self):
#         """ Gets the directory for the output. This is saved
#             as a container and available for the previous step.
#         """
#
#     def get_solution_output_json(self):
#         """ Returns the JSON file in the get_output_dir() """
#
#     def write_environment_info(self):
#         try:
#             print('input dir: %s' % self.get_input_dir())
#         except NotAvailable:
#             print('input dir: not available')
#         print('output dir: %s' % self.get_output_dir())
#         print('temp dir: %s' % self.get_temp_dir())
#         try:
#             print('last_step dir: %s' % self.get_previous_step_dir())
#         except NotAvailable:
#             print('last_step dir: not available')

#
# cie.set_score(name, value, description)
#
# # Only evaluator
# def evaluator_wait_for_solution_to_finish(self):
#     """ (Evaluator) Wait for solution file to be created. """
#     fn = self.get_solution_output_json()
#     TIMEOUT = 10
#     t0 = time.time()
#     while not os.path.exists(fn):
#         cslogger.debug('Output %s not ready yet' % fn)
#         if time.time() - t0 > TIMEOUT:
#             msg = 'Timeout.'
#             raise Exception(msg)
#         time.sleep(1)
#
# def evaluator_wait_for_json_output(self):
#     """ (Evaluator only) returns the json"""
#     self.evaluator_wait_for_solution_to_finish()
#
#     fn = self.get_solution_output_json()
#     try:
#         result = json.loads(open(fn).read())
#     except Exception as e:
#         msg = 'Cannot parse solution output %s' % e
#         raise Exception(msg)  # XXX
#
#     return result
#
# def set_scores(self, scores):
#     self.scores = scores
#
# def has_scores(self):
#     return self.scores is not None
#
# def get_scores(self):
#     assert self.has_scores()
#     return self.scores

#
# class ChallengeInterfaceSolution(ChallengeInterface):
#
#     def get_previous_step_dir(self):
#         """
#             In case this is a multi-step challenge, returns the location
#             of the output data for the previous step.
#
#             Raises NotAvailable if not available.
#         """
#
#     def get_solution_temp_dir(self):
#         """ Gets the directory for writing temporary file. This is erased
#             after the run. """
#
#     def get_input_dir(self):
#         """ Gets the directory for the input.
#
#             Raises NotAvailable if not available.
#         """
#
#     def declare_success(self, data):
#         """ Declares success and writes the output data for challenges
#             that have a JSON file as an output. """
#         res = json.dumps(data)
#         data['ok'] = True
#         fn = os.path.join(self.output_dir, OUTPUT_JSON)
#         with open(fn, 'w') as f:
#             f.write(res)
#
#     def declare_failure(self, error_msg):
#         """ Declares failure with the given error message.
#             Writes the output data for challenges that have a JSON file as an output. """
#         data['ok'] = False
#         res = json.dumps(data)
#         fn = os.path.join(self.output_dir, OUTPUT_JSON)
#         with open(fn, 'w') as f:
#             f.write(res)

#
# def evaluator_set_result(self, status, message):
#     data = {}
#     data['status'] = status
#     data['message'] = message
#
#     fn = os.path.join(self.get_solution_output_json(), 'out.yaml')
#     res = yaml.dump(data)
#     with open(fn, 'w') as f:
#         f.write(res)
#
# # only solution
# def solution_write_output(self, data):
#     """
#         :param data: a dict that is JSON serializable
#     """
#     fn = self.get_solution_output_json()
#     try:
#         s = json.dumps(data, indent=4)
#         with open(fn, 'w') as f:
#             f.write(s)
#     except Exception as e:
#         msg = 'Cannot write solution output %s' % e
#         raise Exception(msg)  # XXX
#
#
#
# def get_input_dir(self):
#     if not self.input_dir:
#         msg = 'There is no input dir defined.'
#         raise NotAvailable(msg)
#     return self.input_dir
#
# def get_output_dir(self):
#     return self.output_dir
#
# def get_solution_output_json(self):
#     return CHALLENGE_SOLUTION_OUTPUT_FILE
#
# def get_temp_dir(self):
#     return self.temp_dir
#
# def get_previous_step_dir(self):
#     if not self.previous_step_dir:
#         msg = 'No temporary dir is defined.'
#         raise NotAvailable(msg)
#     return self.previous_step_dir


def wrap_evaluator(func, ci=None):
    """

        The function is given a ChallengeInterface.

        It might raise InvalidSubmission

    :param func:
    :return:
    """
    if ci is None:
        ci = ChallengeInterfaceEvaluator()

    try:
        func(ci)
    except InvalidSubmission as e:
        status = STATUS_FAILED
        msg = 'Invalid submission:\n\n%s' % indent('  > ', str(e))
    except Exception as e:
        status = STATUS_FAULT
        msg = 'Evaluator fault:\n\n%s' % indent('  > ', str(e))
    else:

        if not ci.has_scores():
            msg = 'Scores not set'
            status = STATUS_FAULT
        else:
            msg = ''
            status = STATUS_SUCCESS

    ci.evaluator_set_result(status, msg)

    # data = json.dumps(out)
    # print(data)
    # output_fn = '/challenge-solution-output/output.json'
    # cslogger.info('Writing to file %s' % output_fn)
    # d = os.path.dirname(output_fn)
    # if not os.path.exists(d):
    #     os.makedirs(d)
    # with open(output_fn, 'w') as f:
    #     f.write(data)
    #
    # cslogger.info('Happy termination.')
    #
    # sys.exit(0)


def wrap_solution(func, ci=None):
    if ci is None:
        ci = ChallengeInterfaceSolution()

    try:
        func(ci)
    except Exception as e:
        cslogger.error(traceback.format_exc(e))
        sys.exit(2)

# def get_challenge_interface():
#     """
#         Gets the ChallengeInterface to use.
#
#         Exits with error code 1 if some of the configuration is missing or invalid.
#     """
#     try:
#         return ConcreteChallengeInterface(CONFIG_LOCATION)
#     except InvalidConfiguration as e:
#         msg = "Invalid configuration: %s" % e
#         cslogger.error(msg)
#         sys.exit(1)


# class ConcreteChallengeInterface(ChallengeInterface):

# def __init__(self, filename):
#     self.scores = None
#     data = yaml.load(open(filename).read())
#
#     try:
#         self.input_dir = data.get('input_dir')
#         self.previous_step_dir = data.get('previous_step_dir')
#         self.output_dir = data.get('output_dir')
#         self.temp_dir = data.get('temp_dir')
#     except KeyError as e:
#         msg = 'Missing configuration option: %s.' % e
#         raise InvalidConfiguration(msg)
#
#     if self.input_dir:
#         if not os.path.exists(self.input_dir):
#             msg = 'Invalid input dir: %s' % self.input_dir
#             raise InvalidConfiguration(msg)
#
#     if self.previous_step_dir:
#         if not os.path.exists(self.previous_step_dir):
#             msg = 'Invalid previous_step_dir dir: %s' % self.previous_step_dir
#             raise InvalidConfiguration(msg)
#
#     if not os.path.exists(self.output_dir):
#         os.makedirs(self.output_dir)
#
#     if not os.path.exists(self.temp_dir):
#         os.makedirs(self.temp_dir)
