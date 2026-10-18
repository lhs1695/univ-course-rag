import re

from app.services.llm import LLM

MAX_SUBQUERIES = 2
MAX_SUBQUERY_CHARS = 200
BROAD_QUERY_MAX_CHARS = 40


def is_broad_procedural(query: str) -> bool:
    query = query.strip()
    return len(query) <= BROAD_QUERY_MAX_CHARS and any(
        word in query for word in ("如何", "怎么", "怎样", "怎么办", "步骤", "方法", "解法", "求法")
    )


def parse_subqueries(raw: str, original: str) -> list[str]:
    original = original.strip().rstrip("？?")
    found = []
    seen = set()
    for line in raw.splitlines():
        line = re.sub(r"^\s*(?:\d+[.、．)）]|[-*•])\s*", "", line).strip()
        line = line[:MAX_SUBQUERY_CHARS]
        key = line.rstrip("？?")
        if not line or key == original or key in seen:
            continue
        seen.add(key)
        found.append(line)
        if len(found) == MAX_SUBQUERIES:
            break
    return found


def expand_subqueries(query: str, llm: LLM) -> list[str]:
    try:
        raw = llm.generate(
            f"把下面宽泛的学生问题改写成2个更具体的检索子问题，每行一个，只输出子问题，不要编号，不要解释。要求：子问题必须指向具体的求解方法、算法步骤或判定准则，避免只问定义；如果该问题在教材中通常对应一种具体方法，应在子问题中写出该方法的名称。\n问题：{query.strip()}"
        )
        return parse_subqueries(raw, query)
    except Exception:  # noqa: BLE001 - any expansion failure must degrade to no subqueries.
        return []
