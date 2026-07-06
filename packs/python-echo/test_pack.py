import json

import pytest

from pack import handle_line


def test_invoke_echoes_input():
    req = json.dumps({"id": "1", "method": "invoke", "input": {"x": 1}})
    reply = json.loads(handle_line(req))
    assert reply == {"id": "1", "result": {"x": 1}}


def test_malformed_line_returns_error():
    reply = json.loads(handle_line("not json"))
    assert reply["id"] is None
    assert reply["error"]["type"] == "bad_request"


def test_unknown_method_returns_error():
    req = json.dumps({"id": "2", "method": "explode", "input": {}})
    reply = json.loads(handle_line(req))
    assert reply["id"] == "2"
    assert reply["error"]["type"] == "unknown_method"


@pytest.mark.parametrize("line", ["5", '"hi"', "[1,2]", "null", "true"])
def test_non_dict_json_returns_bad_request(line):
    reply = json.loads(handle_line(line))
    assert reply == {
        "id": None,
        "error": {"type": "bad_request", "message": reply["error"]["message"]},
    }
