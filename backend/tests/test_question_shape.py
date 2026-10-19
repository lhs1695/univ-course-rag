import pytest
from app.services.question_shape import (
    definition_term,
    evidence_context_order,
    is_contextual_followup,
    is_meaningless_question,
)


@pytest.mark.parametrize("query", ["？！…", "@#$%^&*", "   ", "∑∞×÷=🙂"])
def test_symbols_have_no_substance(query):
    assert is_meaningless_question(query)


@pytest.mark.parametrize("query", ["1+2=?", "What is CDF?", "计算 P(X≤3)", "é", "𠀀"])
def test_letters_and_numbers_have_substance(query):
    assert not is_meaningless_question(query)


@pytest.mark.parametrize("query", [
    "那它有什么性质？", "这是什么意思？", "它呢？", "其定义呢？", "为什么？",
    "为什么会这样？", "呢？", "怎么计算？", "有哪些性质？",
])
def test_short_followups(query):
    assert is_contextual_followup(query)


@pytest.mark.parametrize("query", [
    "什么是分布函数？", "分布函数的定义是什么？", "为什么矩阵乘法不满足交换律？",
    "随机变量有什么性质？", "What is CDF?", "这" + "完整独立问题" * 12,
])
def test_independent_or_long_questions(query):
    assert not is_contextual_followup(query)


@pytest.mark.parametrize(("query", "term"), [
    ("什么是随机变量的分布函数？", "随机变量的分布函数"),
    ("随机变量的分布函数的定义是什么？", "随机变量的分布函数"),
    ("分布函数的定义是什么？", "分布函数"),
    ("请问什么是线性变换？", "线性变换"),
    ("分布函数是指什么？", "分布函数"),
    ("什么是？", ""), ("什么是***？", ""), ("计算1+2", ""), ("分布函数", ""),
    ("明天彩票号码是什么", ""), ("计算结果是什么？", ""),
])
def test_definition_term(query, term):
    assert definition_term(query) == term


def test_summaries_only_move_behind_equal_score_evidence_stably():
    evidence = [
        (1.0, "阶段总结"), (1.0, "定义正文"), (1.0, "本章小结"),
        (1.0, "方法正文"), (0.9, "更低分正文"), (0.8, "总结"),
    ]
    assert evidence_context_order(evidence) == [1, 3, 0, 2, 4, 5]
    assert evidence_context_order([]) == []


@pytest.mark.parametrize("marker", ["阶段总结", "课程内容回顾", "内容回顾", "本章小结", "总结"])
def test_summary_markers(marker):
    assert evidence_context_order([(1, marker), (1, "定义")]) == [1, 0]
