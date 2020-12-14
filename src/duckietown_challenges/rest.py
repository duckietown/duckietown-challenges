# coding=utf-8
import json
import os
import socket
from json import JSONDecodeError
from typing import Any, Union

import termcolor
from six.moves import urllib
from zuper_commons.types import ZException, ZTypeError

from . import logger
from .challenges_constants import ChallengesConstants
from .constants import HEADER_MESSAGING_TOKEN


class Storage:
    done = False


def get_duckietown_server_url() -> str:
    V = ChallengesConstants.DTSERVER_ENV_NAME
    default = ChallengesConstants.DEFAULT_DTSERVER
    if V in os.environ:
        use = os.environ[V]
        if not Storage.done:
            if use != default:
                msg = f"Using server {use} instead of default {default}"
                logger.debug(msg)
            Storage.done = True
        return use
    else:
        return default


class RequestException(ZException):
    pass


class ServerIsDown(RequestException):
    pass


class ServerConnectionError(RequestException):
    """ The server could not be reached or completed request or
        provided an invalid or not well-formatted answer. """


class NotAuthorized(RequestException):
    pass


class NotFound(RequestException):
    pass


class RequestFailed(RequestException):
    """
        The server said the request was invalid.

        Answered  {'ok': False, 'error': msg}
    """


from urllib.parse import urlencode


def make_server_request(
    token: str,
    endpoint: str,
    data=None,
    method: str = "GET",
    timeout: int = None,
    suppress_user_msg: bool = False,
    query_string: Union[str, dict] = None,
) -> Any:
    """
        Raise RequestFailed or ServerConnectionError.

        Returns the result in 'result'.
    """
    if timeout is None:
        timeout = ChallengesConstants.DEFAULT_TIMEOUT

    # import urllib.request

    server = get_duckietown_server_url()
    url = server + endpoint
    # logger.debug(url=url)
    headers = {}
    if token is not None:
        headers[HEADER_MESSAGING_TOKEN] = token

    if data is not None:
        data = json.dumps(data)

        data_sent = data.encode("utf-8")
    else:
        data_sent = None
    # t0 = time.time()
    # dtslogger.info('server request with timeout %s' % timeout)
    if query_string is not None:
        if isinstance(query_string, str):
            url += "?" + query_string
        elif isinstance(query_string, dict):
            qs = urlencode(query_string)
            url += "?" + qs
        else:
            raise ZTypeError(query_string=query_string)
    req = urllib.request.Request(url, headers=headers, data=data_sent)
    req.get_method = lambda: method

    context = dict(
        endpoint=endpoint,
        method=method,
        # data_sent=data,
        timeout=timeout,
    )
    try:
        # dtslogger.info('urlopen')
        res = urllib.request.urlopen(req, timeout=timeout)

        # dtslogger.info('read')
        data_read = res.read()

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")

        # XXX: temporary solution with new interface
        try:
            result = json.loads(err_msg)
            received_msg = result.get("msg", None)
        except JSONDecodeError:

            if e.code == 401:
                msg = "Not authorized to perform operation."
                msg += f"\n\n{err_msg}"
                raise NotAuthorized(msg, **context) from None

            if e.code == 404:
                msg = "Cannot find the specified object"
                msg += f"\n\n{err_msg}"
                raise NotFound(msg, **context) from None

            if e.code == 502:
                msg = "502: The server is currently offline"
                msg += f"\n\n{err_msg}"
                raise NotFound(msg, **context) from None

            msg = f"Cannot read answer from server {url}"
            # msg += "\n\n" + indent(err_msg, "  > ")
            raise ServerConnectionError(msg, err_msg=err_msg, **context) from e

        except (ValueError, KeyError) as e:
            msg = "Cannot read answer from server."
            # msg += "\n\n" + indent(err_msg, "  > ")
            raise ServerConnectionError(msg, err_msg=err_msg, **context) from e

        if e.code == 400:
            msg = "Invalid request to server."
            msg += f"\n\n{received_msg}"
            raise RequestFailed(msg, **context) from None

        if e.code == 401:
            msg = "Not authorized to perform operation."
            msg += f"\n\n{received_msg}"
            raise NotAuthorized(msg, **context) from None

        if e.code == 404:
            msg = "Cannot find the specified object"
            msg += f"\n\n{received_msg}"
            raise NotFound(msg, **context) from None

        msg = f"Operation failed for {url}: {e}"
        msg += f"\n\n{err_msg}"
        raise ServerConnectionError(msg) from e
    except urllib.error.URLError as e:
        if "61" in str(e.reason):
            msg = f"Server is temporarily down; cannot open url {url}"
            raise ServerIsDown(msg, **context) from None
        msg = f"Cannot connect to server {url}:\n{e}"
        raise ServerConnectionError(msg, **context) from e
    except socket.timeout:
        msg = "Timeout while connecting to server. This is either the server's fault or your fault,"
        raise ServerConnectionError(msg, **context) from None

    # delta = time.time() - t0
    # dtslogger.info('server request took %.1f seconds' % delta)

    data_s = data_read.decode("utf-8")
    try:
        result = json.loads(data_s)
    except ValueError as e:
        msg = "Cannot read answer from server."
        # msg += "\n\n" + indent(data_s, "  > ")
        raise ServerConnectionError(msg, data_s=data_s) from e

    if not isinstance(result, dict) or "ok" not in result:
        msg = 'Server provided invalid JSON response. Expected a dict with "ok" in it.'

        raise ServerConnectionError(msg, result=result, **context)

    if "user_msg" in result and not suppress_user_msg:
        user_msg = result["user_msg"]
        if user_msg:
            s = []
            lines = user_msg.strip().split("\n")
            prefix = "message from server: "
            p2 = ": ".rjust(len(prefix))
            print("")

            for i, l in enumerate(lines):
                p = prefix if i == 0 else p2
                # l = termcolor.colored(l, 'blue')
                s.append(termcolor.colored(p, attrs=["dark"]) + l)

            print("\n".join(s))

    if result["ok"]:
        if "result" not in result:
            msg = 'Server provided invalid JSON response. Expected a field "result".'

            raise ServerConnectionError(msg, result=result, **context)

        return result["result"]
    else:
        msg = result.get("msg", f"no error message in {result} ")
        msg = f"Failed request for {url}:\n{msg}"
        raise RequestFailed(msg)
