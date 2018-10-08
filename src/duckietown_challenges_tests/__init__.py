from .read_challenge_definition import *
from .test_interaction import *
from .test_interaction_two_steps import *


def jobs_comptests(context):
    # instantiation
    # from comptests import jobs_registrar
    from comptests.registrar import jobs_registrar_simple
    jobs_registrar_simple(context)
