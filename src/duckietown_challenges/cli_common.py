from contextlib import contextmanager
from dataclasses import dataclass

from .exceptions import InvalidConfiguration
from .rest import NotAuthorized, NotFound, ServerIsDown

__all__ = ["ChallengeEnvironment", "wrap_server_operations"]


@dataclass
class ChallengeEnvironment:
    token: str
    docker_username: str
    docker_password: str


@contextmanager
def wrap_server_operations():
    try:
        yield
    except ServerIsDown as e:
        msg = "Server is down; try again later."
        msg += f"\n\n{e}"
        raise InvalidConfiguration(msg) from None

    except NotAuthorized as e:
        # msg = 'You are not authorized to perform the operation.'
        # msg += f'\n\n{e}'
        msg = str(e)
        raise InvalidConfiguration(msg) from None
    except NotFound as e:
        msg = str(e)
        raise InvalidConfiguration(msg) from None
