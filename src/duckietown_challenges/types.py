from typing import NewType, TypedDict

RPath = NewType("RPath", str)
JobStatusString = NewType("JobStatusString", str)
StepName = NewType("StepName", str)
ChallengeName = NewType("ChallengeName", str)
JobID = NewType("JobID", int)
EvaluatorID = NewType("EvaluatorID", int)
EvaluationFeatureID = NewType("EvaluationFeatureID", int)
UserID = NewType("UserID", int)
SubmissionID = NewType("SubmissionID", int)
ChallengeID = NewType("ChallengeID", int)
ChallengeStepID = NewType("ChallengeStepID", int)
ServiceName = NewType("ServiceName", str)
ComponentID = NewType("ComponentID", int)


class RESTResult(TypedDict, total=False):
    result: object
    ok: bool
    user_msg: str
    total: int  # if present, how much more data
