from typing import cast, List

from nose.tools import assert_equal

from duckietown_challenges import (
    ChallengesConstants as CS,
    ChallengeTransitions,
    from_steps_transitions,
    STATE_ERROR,
    STATE_FAILED,
    STATE_START,
    STATE_SUCCESS,
    StepName,
)
from . import logger


def test_challenges_steps1():
    steps = cast(List[StepName], ["a", "b", "c"])
    transitions = [
        [STATE_START, CS.STATUS_JOB_SUCCESS, "a"],
        [STATE_START, CS.STATUS_JOB_SUCCESS, "b"],
        [STATE_START, CS.STATUS_JOB_SUCCESS, "c"],
        ["a", CS.STATUS_JOB_ERROR, STATE_ERROR],
        ["b", CS.STATUS_JOB_ERROR, STATE_ERROR],
        ["c", CS.STATUS_JOB_ERROR, STATE_ERROR],
        ["a", CS.STATUS_JOB_FAILED, STATE_FAILED],
        ["b", CS.STATUS_JOB_FAILED, STATE_FAILED],
        ["c", CS.STATUS_JOB_FAILED, STATE_FAILED],
        ["a,b,c", CS.STATUS_JOB_SUCCESS, STATE_SUCCESS],
    ]
    ct: ChallengeTransitions = from_steps_transitions(steps, transitions)
    t2 = ct.as_list()
    ct2 = from_steps_transitions(steps, t2)
    logger.info(ct=ct, ct2=ct2)

    assert_equal(transitions, t2)

    logger.info(f"{ct!r}")
    g = ct.get_graph()
    o = ct.top_ordered()
    logger.info(topo=o)

    complete, status, todo = a = ct.get_next_steps({STATE_START: CS.STATUS_JOB_SUCCESS})

    logger.info(a=a)
    assert_equal(complete, False)
    assert_equal(status, None)
    assert_equal(todo, ["a", "b", "c"])

    complete, status, todo = a = ct.get_next_steps(
        {STATE_START: CS.STATUS_JOB_SUCCESS, "a": CS.STATUS_JOB_SUCCESS}
    )

    logger.info(a=a)
    assert_equal(complete, False)
    assert_equal(status, None)
    assert_equal(todo, ["b", "c"])

    complete, status, todo = a = ct.get_next_steps(
        {STATE_START: CS.STATUS_JOB_SUCCESS, "a": CS.STATUS_JOB_ERROR}
    )

    logger.info(a=a)
    assert_equal(complete, True)
    assert_equal(status, CS.STATUS_JOB_ERROR)
    assert_equal(todo, ["b", "c"])

    complete, status, todo = a = ct.get_next_steps(
        {STATE_START: CS.STATUS_JOB_SUCCESS, "a": CS.STATUS_JOB_FAILED}
    )

    logger.info(a=a)
    assert_equal(complete, True)
    assert_equal(status, CS.STATUS_JOB_FAILED)
    assert_equal(todo, ["b", "c"])

    complete, status, todo = a = ct.get_next_steps(
        {
            STATE_START: CS.STATUS_JOB_SUCCESS,
            "a": CS.STATUS_JOB_SUCCESS,
            "b": CS.STATUS_JOB_SUCCESS,
            "c": CS.STATUS_JOB_SUCCESS,
        }
    )

    logger.info(a=a)
    assert_equal(complete, True)
    assert_equal(status, CS.STATUS_JOB_SUCCESS)
    assert_equal(todo, [])
