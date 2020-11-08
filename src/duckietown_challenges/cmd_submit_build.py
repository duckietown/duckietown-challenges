from dataclasses import dataclass
from typing import Optional

__all__ = ["submission_read"]

#
# @dataclass
# class BuildResult:
#     registry: Optional[str]
#     organization: str
#     repository: str
#     tag: str
#     digest: Optional[str]
#
#     def __post_init__(self):
#         if self.repository:
#             assert not "@" in self.repository, self
#         if self.tag:
#             assert not "@" in self.tag, self
#
#         if self.digest is not None:
#             if not self.digest.startswith("sha256"):
#                 msg = f"Unknown digest format: {self.digest} "
#                 raise ValueError(msg)
#             if self.digest.startswith("sha256:sha256"):
#                 msg = f"What happened here? {self.digest} "
#                 raise ValueError(msg)


# localhost:5000/andreacensi/aido2_simple_prediction_r1-step1-simulation-evaluation:2019_04_03_20_03_28@sha256
# :9c1ed66dc31ad9f1b6e454448f010277e38edf051f15b56ff985ec4292290614


#
# def get_complete_tag(br: BuildResult):
#     complete = f"{br.organization}/{br.repository}"
#     if br.tag:
#         complete += f":{br.tag}"
#     if br.registry:
#         complete = f"{br.registry}/{complete}"
#     if br.digest:
#         complete += f"@{br.digest}"
#     return complete
