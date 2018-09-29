import yaml
from comptests import comptest, run_module_tests

from duckietown_challenges.challenge import ChallengeDescription

# language=yaml
data = """

name: "challenge-short"
title: "The title"
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
  group:de:
    grant: false
    moderate: true
    snoop: true

steps:

  step1:
    title: Step 1
    description: |
      Description in Markdown
    evaluation_parameters:
      image: Image/name
    features_required:
      arm: true
      ram_mb: 8000

  step2:
    title: Step 2
    description: |
      Description in Markdown
    evaluation_parameters:
      image: Image/name
    features_required:
      arm: true
      ram_mb: 8000
      
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
    print y
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




if __name__ == '__main__':
    run_module_tests()
