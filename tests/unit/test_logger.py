import logging

from logger import (
    RequestIdFilter,
    ensure_request_id_filter,
    get_log_format,
    reset_request_id,
    set_request_id,
)


def test_log_format_includes_request_id_for_info():
    fmt = get_log_format(logging.INFO)
    assert "%(request_id)s" in fmt


def test_log_format_includes_request_id_for_debug():
    fmt = get_log_format(logging.DEBUG)
    assert "%(request_id)s" in fmt


def test_request_id_filter_injects_context_value():
    log_record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    token = set_request_id("job-abc")

    try:
        request_id_filter = RequestIdFilter()
        assert request_id_filter.filter(log_record) is True
        assert log_record.request_id == "job-abc"
    finally:
        reset_request_id(token)


def test_ensure_request_id_filter_attaches_only_once():
    handler = logging.StreamHandler()

    ensure_request_id_filter(handler)
    ensure_request_id_filter(handler)

    request_id_filters = [f for f in handler.filters if isinstance(f, RequestIdFilter)]
    assert len(request_id_filters) == 1
