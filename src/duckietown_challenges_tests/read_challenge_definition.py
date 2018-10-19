import yaml
from comptests import comptest, run_module_tests

from duckietown_challenges.challenge import ChallengeDescription, ServiceDefinition, EvaluationParameters
# language=yaml
from duckietown_challenges.utils import InvalidConfiguration

data = """

challenge: "challenge-short"
title: "The title"

tags: [tag1]
description: |

  Description in Markdown.

protocol: p2

date-open: 2001-12-14t21:59:43.10-05:00
date-close: 2001-12-14t21:59:43.10-05:00

roles:
  user:AndreaCensi:
    grant: true
    moderate: true
    snoop: true
  # group:de:
  #   grant: false
  #   moderate: true
  #   snoop: true

scoring:
    scores:
        - name: score1
          description: description
          
steps:

  step1:
    title: Step 1
    description: |
      Description in Markdown
    evaluation_parameters:
        version: '3'
        services:
            evaluator:
                image: Image/name
            solution:
                image: SUBMISSION_CONTAINER
            
    timeout: 100
    features_required:
      arm: true
      ram_mb: 8000

  step2:
    title: Step 2
    description: |
      Description in Markdown
    evaluation_parameters:
        version: '3'
        services:
            evaluator:
                image: Image/name
                environment: {}
            solution:
                image: SUBMISSION_CONTAINER            
    features_required:
      arm: true
      ram_mb: 8000
    timeout: 100
        
        
transitions:
  # We start with the state START triggering step1
  - [START, success, step1]
  # If step1 succeeds then we go on to step2
  - [step1, success, step2]
  # # If step1 fails, then we finish
  - [step1, failed, FAILED]
  - [step1, error, ERROR]
  # if Step2 finishes, all good 
  - [step2, success, SUCCESS]
  # Otherwise error
  - [step2, failed, FAILED]
  - [step2, error, ERROR]
  


"""


@comptest
def read_challenge_1():
    d = yaml.load(data)

    c0 = ChallengeDescription.from_yaml(d)

    y = c0.as_yaml()
    d2 = yaml.load(y)
    print(y)
    c = ChallengeDescription.from_yaml(d2)

    assert c.title
    assert len(c.get_steps()) == 2

    status = {'START': 'success'}
    complete, _, steps = c.get_next_steps(status)
    assert not complete
    assert steps == ['step1'], steps

    status['step1'] = 'evaluating'
    complete, _, steps = c.get_next_steps(status)
    assert not complete
    assert steps == [], steps

    status['step1'] = 'success'
    complete, _, steps = c.get_next_steps(status)
    assert not complete
    assert steps == ['step2'], steps

    status['step1'] = 'error'
    complete, result, steps = c.get_next_steps(status)
    assert complete
    assert result == 'error'
    assert steps == [], steps

    status['step1'] = 'failed'
    complete, result, steps = c.get_next_steps(status)
    assert complete
    assert result == 'failed'
    assert steps == [], steps

    status['step1'] = 'success'
    status['step2'] = 'success'
    complete, result, steps = c.get_next_steps(status)
    assert complete
    assert result == 'success', result
    assert steps == [], steps

    status['step1'] = 'success'
    status['step2'] = 'evaluating'
    complete, result, steps = c.get_next_steps(status)
    assert not complete
    assert result is None, result
    assert steps == [], steps

    status['step1'] = 'success'
    status['step2'] = 'failed'
    complete, result, steps = c.get_next_steps(status)
    assert complete
    assert result == 'failed', result
    assert steps == [], steps

    status['step1'] = 'success'
    status['step2'] = 'error'
    complete, result, steps = c.get_next_steps(status)
    assert complete
    assert result == 'error', result
    assert steps == [], steps


@comptest
def empty_services():
    data = """
version: '3'
services:

"""
    assert_raises_s(InvalidConfiguration, 'Expected dict', test_reading_evaluation_parameters, data)


@comptest
def empty_services2():
    data = """
version: '3'
services: {}

"""
    assert_raises_s(InvalidConfiguration, 'No services described', test_reading_evaluation_parameters, data)


@comptest
def missing_services():
    data = """
version: '3'


"""
    assert_raises_s(InvalidConfiguration, "'services'", test_reading_evaluation_parameters, data)


@comptest
def extra_field():
    data = """
version: '3'
services:
    one:
        image: image
    solution:
        image: SUBMISSION_CONTAINER
another:
"""
    assert_raises_s(InvalidConfiguration, "'another'", test_reading_evaluation_parameters, data)


def assert_raises_s(E, contained, f, *args):
    try:
        f(*args)
    except E as e:
        s = str(e)
        if contained not in s:
            msg = 'Expected %r in error:\n%s' % (contained, s)
            raise Exception(msg)
    else:
        msg = 'Expected to find exception %s' % str(E)
        raise Exception(msg)


def test_reading(s):
    d = yaml.load(s)
    c0 = ChallengeDescription.from_yaml(d)
    return c0


def test_reading_service(s):
    d = yaml.load(s)
    c0 = ServiceDefinition.from_yaml(d)
    return c0


def test_reading_evaluation_parameters(s):
    d = yaml.load(s)
    c0 = EvaluationParameters.from_yaml(d)
    return c0


if __name__ == '__main__':
    run_module_tests()
