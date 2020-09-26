import argparse
import dataclasses
import json
import os
from typing import List

import termcolor

from . import logger
from .cli_common import ChallengeEnvironment, wrap_server_operations
from .cmd_submit_build import submission_build
from .constants import get_duckietown_server_url
from .exceptions import InvalidConfiguration
from .rest_methods import (
    dtserver_get_compatible_challenges,
    dtserver_retire_same_label,
    dtserver_submit2,
    get_registry_info,
)
from .submission_read import read_submission_info

__all__ = ["dt_challenges_cli_submit"]


def dt_challenges_cli_submit(args: List[str], environment: ChallengeEnvironment):
    prog = "dts challenges submit"
    usage = """


    Submission:

        %(prog)s --challenge NAME



    ## Building options

    Rebuilds ignoring Docker cache

        %(prog)s --no-cache



    ## Attaching user data

    Submission with an identifying label:

        %(prog)s --user-label  "My submission"

    Submission with an arbitrary JSON payload:

        %(prog)s --user-meta  '{"param1": 123}'




    """
    parser = argparse.ArgumentParser(prog=prog, usage=usage)

    group = parser.add_argument_group("Submission identification")
    parser.add_argument("--challenge", help="Specify challenge name.", default=None)
    group.add_argument(
        "--user-label", dest="message", default=None, type=str, help="Submission message",
    )
    group.add_argument(
        "--user-meta",
        dest="metadata",
        default=None,
        type=str,
        help="Custom JSON structure to attach to the submission",
    )

    group = parser.add_argument_group("Building settings.")

    group.add_argument("--no-cache", dest="no_cache", action="store_true", default=False)
    group.add_argument("--impersonate", type=int, default=None)

    group.add_argument(
        "--retire-same-label",
        action="store_true",
        default=False,
        help="Retire my submissions with the same label.",
    )

    group.add_argument("-C", dest="cwd", default=None, help="Base directory")

    parsed = parser.parse_args(args)
    impersonate = parsed.impersonate
    if parsed.cwd is not None:
        logger.info("Changing to directory %s" % parsed.cwd)
        os.chdir(parsed.cwd)

    if not os.path.exists("submission.yaml"):
        msg = "Expected a submission.yaml file in %s." % (os.path.realpath(os.getcwd()))
        raise InvalidConfiguration(msg)

    sub_info = read_submission_info(".")

    token = environment.token
    logger.info(f"token: {token}")

    with wrap_server_operations():
        ri = get_registry_info(token=token, impersonate=impersonate)

        registry = ri.registry

        compat = dtserver_get_compatible_challenges(
            token=token, impersonate=impersonate, submission_protocols=sub_info.protocols,
        )
        if not compat.compatible:
            msg = (
                "There are no compatible challenges with protocols %s,\n"
                " or you might not have the necessary permissions." % sub_info.protocols
            )
            raise InvalidConfiguration(msg)

        if parsed.message:
            sub_info.user_label = parsed.message
        if parsed.metadata:
            sub_info.user_metadata = json.loads(parsed.metadata)
        if parsed.challenge:
            sub_info.challenge_names = parsed.challenge.split(",")
        if sub_info.challenge_names is None:
            msg = "You did not specify a challenge. I will use the first compatible one."
            print(msg)
            sub_info.challenge_names = [list(compat.compatible)[0]]

        if sub_info.challenge_names == ["all"]:
            sub_info.challenge_names = compat.compatible

        print("I will submit to the challenges %s" % sub_info.challenge_names)

        for c in sub_info.challenge_names:
            if not c in compat.available_submit:
                msg = 'The challenge "%s" does not exist among %s.' % (c, list(compat.available_submit),)
                raise InvalidConfiguration(msg)
            if not c in compat.compatible:
                msg = 'The challenge "%s" is not compatible with protocols %s .' % (c, sub_info.protocols,)
                raise InvalidConfiguration(msg)
        username = environment.docker_username

        print("")
        print("")
        br = submission_build(username=username, registry=registry, no_cache=parsed.no_cache)

        data = {
            "image": dataclasses.asdict(br),
            "user_label": sub_info.user_label,
            "user_payload": sub_info.user_metadata,
            "protocols": sub_info.protocols,
        }

        submit_to_challenges = sub_info.challenge_names

        if parsed.retire_same_label and sub_info.user_label:

            retired = dtserver_retire_same_label(
                token=token, impersonate=impersonate, label=sub_info.user_label
            )
            if retired:
                print(f"I retired the following submissions with the same label: {retired}")
            else:
                print(f"No submissions with the same label available.")

        data = dtserver_submit2(
            token=token, challenges=submit_to_challenges, data=data, impersonate=impersonate,
        )

        # print('obtained:\n%s' % json.dumps(data, indent=2))
        component_id = data["component_id"]
        submissions = data["submissions"]
        # url_component = href(get_duckietown_server_url() + '/humans/components/%s' % component_id)

        msg = f"""

        Successfully created component.

        This component has been entered in {len(submissions)} challenge(s).

                """

        for challenge_name, sub_info2 in submissions.items():
            submission_id = sub_info2["submission_id"]
            url_submission = href(get_duckietown_server_url() + "/humans/submissions/%s" % submission_id)
            challenge_title = sub_info2["challenge"]["title"]
            submission_id_color = termcolor.colored(submission_id, "cyan")
            P = dark("$")
            head = bright(f"## Challenge {challenge_name} - {challenge_title}")
            msg += (
                "\n\n"
                + f"""

        {head}

        Track this submission at:

            {url_submission}

        You can follow its fate using:

            {P} dts challenges follow --submission {submission_id_color}

        You can speed up the evaluation using your own evaluator:

            {P} dts challenges evaluator --submission {submission_id_color}

        """.strip()
            )
            manual = href("https://docs.duckietown.org/daffy/AIDO/out/")
            msg += f"""

        For more information, see the manual at {manual}
        """

        print(msg)

    extra = set(submissions) - set(submit_to_challenges)

    if extra:
        msg = f"""
    Note that the additional {len(extra)} challenges ({cute_list(extra)}) are required checks
    before running the code on the challenges you chose ({cute_list(submit_to_challenges)}).
    """
        print(msg)


def cute_list(x):
    return ", ".join(x)


def bright(x):
    return termcolor.colored(x, "blue")


def dark(x):
    return termcolor.colored(x, attrs=["dark"])


def href(x):
    return termcolor.colored(x, "blue", attrs=["underline"])
