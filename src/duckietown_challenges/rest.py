# coding=utf-8
import json
import os
from json import JSONDecodeError

import termcolor

from duckietown_challenges import ChallengesConstants
from . import dclogger
from .utils import indent


class Storage(object):
    done = False


def get_duckietown_server_url():
    V = 'DTSERVER'
    default = ChallengesConstants.DEFAULT_DTSERVER
    if V in os.environ:
        use = os.environ[V]
        if not Storage.done:
            if use != default:
                msg = 'Using server %s instead of default %s' % (use, default)
                dclogger.info(msg)
            Storage.done = True
        return use
    else:
        return default


class RequestException(Exception):
    pass


class ServerIsDown(RequestException):
    pass


class ConnectionError(RequestException):
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


def make_server_request(token,
                        endpoint,
                        data=None,
                        method: str = 'GET',
                        timeout: int = None,
                        suppress_user_msg: bool = False):
    """
        Raise RequestFailed or ConnectionError.

        Returns the result in 'result'.
    """
    if timeout is None:
        timeout = ChallengesConstants.DEFAULT_TIMEOUT

    from six.moves import urllib
    # import urllib.request

    server = get_duckietown_server_url()
    url = server + endpoint

    headers = {}
    if token is not None:
        headers['X-Messaging-Token'] = token

    if data is not None:
        data = json.dumps(data)

        data = data.encode('utf-8')
    # t0 = time.time()
    # dtslogger.info('server request with timeout %s' % timeout)
    req = urllib.request.Request(url, headers=headers, data=data)
    req.get_method = lambda: method

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
            received_msg = result.get('msg', None)
        except JSONDecodeError:

            if e.code == 401:
                msg = 'Not authorized to perform operation.'
                msg += f'\n\n{err_msg}'
                raise NotAuthorized(msg) from None

            if e.code == 404:
                msg = 'Cannot find the specified object'
                msg += f'\n\n{err_msg}'
                raise NotFound(msg) from None
            msg = 'Cannot read answer from server.'
            msg += '\n\n' + indent(err_msg, '  > ')
            raise ConnectionError(msg) from e

        except (ValueError, KeyError) as e:
            msg = 'Cannot read answer from server.'
            msg += '\n\n' + indent(err_msg, '  > ')
            raise ConnectionError(msg) from e

        if e.code == 401:
            msg = 'Not authorized to perform operation.'
            msg += f'\n\n{received_msg}'
            raise NotAuthorized(msg) from None

        if e.code == 404:
            msg = 'Cannot find the specified object'
            msg += f'\n\n{received_msg}'
            raise NotFound(msg) from None

        msg = 'Operation failed for %s: %s' % (url, e)
        msg += f'\n\n{err_msg}'
        raise ConnectionError(msg) from e
    except urllib.error.URLError as e:
        if '61' in str(e.reason):
            msg = 'Server is temporarily down; cannot open %s' % url
            raise ServerIsDown(msg) from None
        msg = 'Cannot connect to server %s:\n%s' % (url, e)
        raise ConnectionError(msg) from e

    # delta = time.time() - t0
    # dtslogger.info('server request took %.1f seconds' % delta)

    data_s = data_read.decode('utf-8')
    try:
        result = json.loads(data_s)
    except ValueError as e:
        msg = 'Cannot read answer from server.'
        msg += '\n\n' + indent(data_s, '  > ')
        raise ConnectionError(msg) from e

    if not isinstance(result, dict) or 'ok' not in result:
        msg = 'Server provided invalid JSON response. Expected a dict with "ok" in it.'
        msg += '\n\n' + indent(data, '  > ')
        raise ConnectionError(msg)

    if 'user_msg' in result and not suppress_user_msg:
        user_msg = result['user_msg']
        if user_msg:
            s = []
            lines = user_msg.strip().split('\n')
            prefix = u'message from server: '
            p2 = u': '.rjust(len(prefix))
            print('')

            for i, l in enumerate(lines):
                p = prefix if i == 0 else p2
                # l = termcolor.colored(l, 'blue')
                s.append(termcolor.colored(p, attrs=['dark']) + l)
            from dt_shell.cli import dts_print

            dts_print('\n'.join(s))

    if result['ok']:
        if 'result' not in result:
            msg = 'Server provided invalid JSON response. Expected a field "result".'
            msg += '\n\n' + indent(result, '  > ')
            raise ConnectionError(msg)
        return result['result']
    else:
        msg = result.get('msg', 'no error message in %s ' % result)
        msg = 'Failed request for %s:\n%s' % (url, msg)
        raise RequestFailed(msg)
