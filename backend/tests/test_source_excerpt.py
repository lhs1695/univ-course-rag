"""Display cleanup must leave the underlying generation evidence intact."""

from uuid import uuid4

import pytest
from app.models.document import Chunk
from app.services.generate import (
    FORMULA_EXCERPT_NOTICE,
    assemble_ask_context,
    clean_source_excerpt,
)
from app.services.retrieve import SearchHit


@pytest.mark.parametrize("noise", [
    "第 12 页 共 30 页", "Page 12 of 30", "12", "— 12 —",
    "CONTENTS", "Contents Chapter 1 .... 12", "目录 第一章",
])
def test_excerpt_removes_footer_page_number_and_contents_lines(noise):
    assert clean_source_excerpt(f"第一段正文。\n{noise}\n第二段正文。") == "第一段正文。 第二段正文。"


@pytest.mark.parametrize("text", [
    r"\frac{x^2}{y_1} + \sum_{i=1}^{n} α_i = β",
    "∑ ∫ √ α β γ = + ×",
])
def test_formula_dense_excerpt_returns_page_notice(text):
    assert clean_source_excerpt(text) == FORMULA_EXCERPT_NOTICE


def test_normal_chinese_excerpt_preserves_content():
    text = "分布函数具有单调不减性，概率取值在零到一之间。"
    assert clean_source_excerpt(text) == text
    assert clean_source_excerpt(f"  {text}\n\t第二段说明。 ") == f"{text} 第二段说明。"


def test_excerpt_removes_sparse_replacement_characters_and_flags_heavy_damage():
    assert clean_source_excerpt("正常中文摘录中�有一处损坏。") == "正常中文摘录中有一处损坏。"
    assert clean_source_excerpt("正文����") == FORMULA_EXCERPT_NOTICE


def test_excerpt_cleanup_does_not_change_prompt_or_stored_chunk():
    text = "分布函数具有单调不减性。\n第 12 页"
    chunk_id = uuid4()
    document_id = uuid4()
    chunk = Chunk(id=chunk_id, document_id=document_id, text=text)
    hit = SearchHit(chunk_id, document_id, 12, "检索摘要", 1.0)
    context = assemble_ask_context("分布函数有什么性质？", [hit], {chunk_id: chunk})
    assert context.source_texts[chunk_id] == "分布函数具有单调不减性。"
    assert f"[Source {chunk_id}]\n{text}\n" in context.prompt
    assert chunk.text == text
