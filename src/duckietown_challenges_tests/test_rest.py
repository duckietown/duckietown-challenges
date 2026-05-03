import json
from unittest.mock import patch

from duckietown_challenges.constants import HEADER_MESSAGING_TOKEN
from duckietown_challenges.rest import DUCKIETOWN_USER_AGENT, make_server_request


class DummyResponse:
    code = 200
    headers: dict[str, str] = {}

    def read(self):
        return json.dumps({"ok": True, "result": {}}).encode("utf-8")


def test_make_server_request_sets_headers():
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["headers"] = dict(request.header_items())
        return DummyResponse()

    with patch(
        "duckietown_challenges.rest.urllib.request.urlopen", side_effect=fake_urlopen
    ):
        make_server_request("dt2-example-token", "/api/user-info")

    assert captured["headers"]["User-agent"] == DUCKIETOWN_USER_AGENT
    assert captured["headers"][HEADER_MESSAGING_TOKEN] == "dt2-example-token"
