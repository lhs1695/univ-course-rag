UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
UPSTREAM_UNAVAILABLE_MESSAGE = "上游 AI 服务暂时不可用，请稍后重试。"


class UpstreamUnavailable(Exception):
    """A provider failure whose details must not reach users or normal logs."""

    error_code = UPSTREAM_UNAVAILABLE
    message = UPSTREAM_UNAVAILABLE_MESSAGE
    status_code = 503


class UpstreamTimeout(UpstreamUnavailable):
    error_code = "UPSTREAM_TIMEOUT"
    message = "上游 AI 服务响应超时，请稍后显式重试。"
    status_code = 504
