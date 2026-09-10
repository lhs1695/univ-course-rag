UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
UPSTREAM_UNAVAILABLE_MESSAGE = "上游 AI 服务暂时不可用，请稍后重试。"


class UpstreamUnavailable(Exception):
    """A provider failure whose details must not reach users or normal logs."""
