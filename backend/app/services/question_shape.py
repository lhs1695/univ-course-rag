"""Bounded, deterministic question rules; no model or retrieval dependencies."""

import re

NEEDS_CONTEXT = "NEEDS_CONTEXT"
NEEDS_CONTEXT_MESSAGE = (
    "这个问题看起来是在接着上一题问，但我这边没有上一题的内容。"
    "请把问题写完整，例如写清你问的是哪个概念。"
)
INVALID_QUESTION = "INVALID_QUESTION"
INVALID_QUESTION_MESSAGE = (
    "这个问题看起来只有标点或符号，没法理解，请写出具体的课程问题。"
)


def is_meaningless_question(query: str) -> bool:
    """Unicode letters/numbers count as substance, including English and math inputs."""
    return not any(char.isalnum() for char in query)


def is_calculation_question(query: str) -> bool:
    """Require both an explicit number and a calculation-intent word."""
    return bool(re.search(r"[\d零〇一二两三四五六七八九十百千万亿]", query)) and any(
        word in query for word in ("求", "计算", "概率", "是多少", "等于", "值")
    )


def is_contextual_followup(query: str) -> bool:
    """Only short demonstratives or explicit subjectless question templates qualify."""
    text = query.strip().rstrip("?？!！。 ")
    if not text or len(text) > 40:
        return False
    if re.match(r"^(那|这|它|其)", text):
        return True
    # Do not treat independent questions such as 为什么矩阵乘法不满足交换律 as followups.
    if re.fullmatch(r"为什么(?:呢|会这样|是这样|如此|这样|会如此)?", text):
        return True
    return bool(re.fullmatch(
        r"(?:呢|然后呢|还有呢|怎么(?:算|计算|理解|证明|做)|如何(?:计算|理解|证明)|"
        r"有(?:什么|哪些)(?:性质|特点|用途)|能举个例子吗)", text
    ))


def definition_term(query: str) -> str:
    """Remove definition-question wrappers without inventing absent subject qualifiers."""
    text = query.strip().rstrip("?？!！。 ")
    # “是什么” also asks for instance values, e.g. tomorrow's lottery numbers.
    # Keep those on their existing retrieval/expansion path rather than treating them as definitions.
    if re.search(r"今天|明天|昨天|号码|结果|答案|数值|\d", text):
        return ""
    patterns = (
        r"^(?:请问|请解释|解释一下)?什么是(.+)$",
        r"^(?:请)?简述(.+?)的(?:含义|意思)$",
        r"^(?:请)?解释(?:一下)?(.+?)(?:的(?:含义|意思|定义))?$",
        r"^(.+?)的(?:含义|意思)(?:是什么|是啥)?$",
        r"^(.+?)的定义(?:是什么|是啥)?$",
        r"^(.+?)(?:是什么|是指什么)$",
        r"^(?:请解释|解释一下)(.+?)的定义$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            term = match.group(1).strip()
            if term in {"含义", "意思", "定义", "一下", "它", "这", "这个", "其"}:
                return ""
            return term if any(char.isalnum() for char in term) else ""
    return ""


def evidence_context_order(evidence: list[tuple[float, str]]) -> list[int]:
    """Stable summary-last ordering inside consecutive exactly equal-score groups only."""
    order: list[int] = []
    start = 0
    while start < len(evidence):
        end = start + 1
        while end < len(evidence) and evidence[end][0] == evidence[start][0]:
            end += 1
        order.extend(sorted(
            range(start, end),
            key=lambda index: bool(re.search(
                r"阶段总结|课程内容回顾|内容回顾|本章小结|总结", evidence[index][1]
            )),
        ))
        start = end
    return order
