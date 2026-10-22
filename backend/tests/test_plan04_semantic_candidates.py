
"""PLAN-04: intent candidates remain candidate; Fake grouping contract."""

from app.services.question_groups import suggest_intent_candidate


def test_plan04_intent_rules_are_candidates_only():
    assert suggest_intent_candidate("什么是向量")["intent_code"] == "concept"
    assert suggest_intent_candidate("怎么求矩阵的秩")["intent_code"] == "procedure"
    assert suggest_intent_candidate("特征值与特征向量的区别")["intent_code"] == "compare"
    assert suggest_intent_candidate("作业什么时候交")["intent_code"] == "admin_oor"
    for text in ("什么是向量", "怎么做", "随便问问"):
        payload = suggest_intent_candidate(text)
        assert payload["intent_status"] == "candidate"
        assert payload["intent_source"] == "rule_v1"
