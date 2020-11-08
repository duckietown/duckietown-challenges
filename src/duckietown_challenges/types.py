from typing import NewType


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
