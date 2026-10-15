"""Synthetic semantic vectors test contracts, never real synonym accuracy."""

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from app.config import ConfigurationUnavailable, Settings
from app.main import app
from app.models.course import CourseMemberRole
from app.models.user import UserRole
from app.services.question_groups import (
    QuestionGroupingError,
    build_question_embedder,
    get_question_embedder,
    group_course_questions,
)
from app.services.upstream import UpstreamTimeout

from tests.conftest import add_user
from tests.test_courses import add_course, add_member, login_as
from tests.test_insights import _add_log


class ScriptedSemanticEmbedder:
    model_name = "scripted-semantic-fixture"
    index_identity = "test-only-scripted-vectors"

    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def embed(self, texts):
        self.calls.append(texts)
        return [self.mapping[text] for text in texts]


def angle(degrees):
    radians = math.radians(degrees)
    return [math.cos(radians), math.sin(radians)]


@pytest.fixture
def context(client, db):
    teacher = add_user(db, "group-observer", "pass", UserRole.teacher)
    course = add_course(db, "Synthetic Groups")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    return course, teacher


def add_question(db, course, user, query, *, outcome="cited_answer", role="student", when=None):
    _add_log(db, course_id=course.id, user_id=user.id, query=query, hit=True,
             error_code=None, created_at=when or datetime.now(UTC) - timedelta(hours=1),
             role=role, outcome=outcome)


def run_groups(db, course, embedder, threshold=0.9):
    return group_course_questions(
        db, course.id, window_start=datetime.now(UTC) - timedelta(days=1),
        window_end=datetime.now(UTC), embedder=embedder, min_similarity=threshold,
    )


def test_synonyms_group_but_same_topic_different_task_and_unrelated_stay_single(db, context):
    course, user = context
    vectors = {
        "什么是事务原子性": angle(0),
        "全部提交或全部撤销是什么意思": angle(5),
        "请写出设置隔离级别的SQL": angle(80),
        "隔离级别概念是什么": angle(120),
        "矩阵的特征值怎么算": angle(180),
    }
    for query in vectors:
        add_question(db, course, user, query)
    add_question(db, course, user, "什么是事务原子性", outcome="no_evidence")
    db.commit()
    embedder = ScriptedSemanticEmbedder(vectors)

    body = run_groups(db, course, embedder)

    assert body["threshold_calibrated"] is False
    assert body["eligible_attempts"] == 6
    assert body["distinct_questions"] == 5
    assert body["grouped_questions"] == 2
    assert body["singleton_questions"] == body["singleton_attempts"] == 3
    candidate = next(group for group in body["groups"] if group["kind"] == "candidate")
    assert candidate["count"] == 3
    assert {row["query"] for row in candidate["members"]} == set(list(vectors)[:2])
    assert candidate["min_pair_similarity"] >= 0.9
    assert sum(row["no_evidence"] for row in candidate["members"]) == 1
    assert len(embedder.calls) == 1


def test_complete_linkage_prevents_transitive_topic_chain(db, context):
    course, user = context
    for query in ("甲任务", "乙任务", "丙任务"):
        add_question(db, course, user, query)
    db.commit()
    embedder = ScriptedSemanticEmbedder(dict(zip(("甲任务", "乙任务", "丙任务"), map(angle, [0, 20, 40]))))
    body = run_groups(db, course, embedder, math.cos(math.radians(25)))
    assert sorted(group["distinct_questions"] for group in body["groups"]) == [1, 2]
    assert all(group["min_pair_similarity"] is None or group["min_pair_similarity"] >= body["min_similarity"]
               for group in body["groups"])


def test_low_similarity_synonym_miss_stays_visible_as_singletons_not_forced_by_words(db, context):
    course, user = context
    queries = ["事务原子性是什么", "如何理解事务原子性"]
    for query in queries:
        add_question(db, course, user, query)
    db.commit()
    # Simulate an embedding miss: disclose the split, do not replace it with lexical rules.
    embedder = ScriptedSemanticEmbedder(dict(zip(queries, [[1, 0], [0, 1]])))
    body = run_groups(db, course, embedder)
    assert body["grouped_questions"] == 0
    assert body["singleton_questions"] == body["singleton_attempts"] == 2
    assert {group["representative"] for group in body["groups"]} == set(queries)


def test_representative_is_actual_medoid_not_most_frequent_or_generated_title(db, context):
    course, user = context
    vectors = {"边界一": angle(0), "中心问句": angle(5), "边界二": angle(10)}
    for query in vectors:
        add_question(db, course, user, query)
    for _ in range(8):
        add_question(db, course, user, "边界一")
    db.commit()
    first = run_groups(db, course, ScriptedSemanticEmbedder(vectors))
    second = run_groups(db, course, ScriptedSemanticEmbedder(vectors))
    assert first["groups"] == second["groups"]
    group = first["groups"][0]
    assert group["representative"] == "中心问句"
    assert group["count"] == 11
    assert next(row for row in group["members"] if row["query"] == "中心问句")["similarity_to_representative"] == 1


@pytest.mark.parametrize("questions", [[], ["  同一问句  ", "同一问句"]])
def test_zero_or_one_distinct_question_never_embeds(db, context, questions):
    course, user = context
    for query in questions:
        add_question(db, course, user, query)
    db.commit()
    embedder = ScriptedSemanticEmbedder({})
    body = run_groups(db, course, embedder)
    assert not body["embedding_called"]
    assert embedder.calls == []
    assert body["singleton_questions"] == bool(questions)
    assert body["singleton_attempts"] == len(questions)


@pytest.mark.parametrize("vectors", [
    None, [], [[1.0, 0.0]], [[1.0], [1.0, 0.0]], [[0, 0], [1, 0]],
    [[float("nan"), 1], [1, 0]], [[float("inf"), 1], [1, 0]],
    [[True, 1], [1, 0]], [["1", 0], [1, 0]], [[1] * 4097, [1] * 4097],
])
def test_invalid_vectors_fail_without_partial_or_lexical_fallback(db, context, vectors):
    course, user = context
    for query in ["测试甲", "测试乙"]:
        add_question(db, course, user, query)
    db.commit()
    embedder = Mock()
    embedder.embed.return_value = vectors
    with pytest.raises(QuestionGroupingError):
        run_groups(db, course, embedder)


def test_course_window_role_outcome_and_full_query_scope(client, db, context):
    course, user = context
    other = add_course(db, "Other Course")
    prefix = "共同长前缀" * 45  # Beyond P4's 200-char display key; P5 must retain the differing task.
    first, second = prefix + "解释定义", prefix + "编写代码"
    now = datetime.now(UTC)
    for target, query, role, outcome, when in [
        (course, first, "student", "cited_answer", now - timedelta(hours=1)),
        (course, second, "student", "no_evidence", now - timedelta(hours=1)),
        (course, "教师资料", "teacher", "cited_answer", now),
        (course, "未知角色", None, "cited_answer", now),
        (course, "过期", "student", "cited_answer", now - timedelta(days=91)),
        (course, "未来", "student", "cited_answer", now + timedelta(hours=1)),
        (other, "别课", "student", "cited_answer", now),
        (course, "失败不入组", "student", "failure", now - timedelta(hours=1)),
        (course, "未知结果", "student", None, now - timedelta(hours=1)),
    ]:
        add_question(db, target, user, query, role=role, outcome=outcome, when=when)
    db.commit()
    embedder = ScriptedSemanticEmbedder({first: [1, 0], second: [0, 1]})
    app.dependency_overrides[get_question_embedder] = lambda: embedder
    response = client.post(f"/courses/{course.id}/insights/groups", json={
        "min_similarity": 0.9, "confirm_external_processing": True,
    })
    assert response.status_code == 200
    body = response.json()
    assert set(embedder.calls[0]) == {first, second}
    assert body["distinct_questions"] == 2
    assert body["eligible_attempts"] == 2
    assert body["excluded_attempts"] == 2
    assert body["singleton_questions"] == 2
    assert "user_id" not in response.text


def test_default_disabled_and_explicit_confirmation_do_not_call_any_embedder(client, db, context):
    course, _ = context
    assert client.get(f"/courses/{course.id}/insights").status_code == 200
    path = f"/courses/{course.id}/insights/groups"
    assert client.post(path, json={"min_similarity": 0.9}).status_code == 422
    response = client.post(path, json={"min_similarity": 0.9, "confirm_external_processing": True})
    assert response.status_code == 503
    assert response.json()["error_code"] == "QUESTION_GROUPING_DISABLED"


@pytest.mark.parametrize("payload", [{}, {"min_similarity": 0}, {"min_similarity": 1.1},
    {"min_similarity": "nan"}, {"min_similarity": 0.9, "start_at": "2026-01-01T00:00:00"}])
def test_threshold_and_window_require_valid_explicit_inputs(client, db, context, payload):
    course, _ = context
    assert client.post(f"/courses/{course.id}/insights/groups", json={
        "confirm_external_processing": True, **payload,
    }).status_code == 422


@pytest.mark.parametrize("backend,embedding", [("embedding", "fake"), ("unknown", "siliconflow")])
def test_fake_hashing_or_unknown_backend_cannot_be_used_as_semantics(backend, embedding):
    with pytest.raises(ConfigurationUnavailable):
        build_question_embedder(Settings(_env_file=None, question_grouping_backend=backend, embedder_backend=embedding))


@pytest.mark.parametrize("blocked", ["student", "outsider", "removed", "anonymous"])
def test_permission_failures_happen_before_provider_resolution(client, db, context, blocked):
    course, _ = context
    student = add_user(db, "outsider-student", "pass", UserRole.student)
    if blocked in {"student", "removed"}:
        add_member(db, course, student, CourseMemberRole.student)
    if blocked == "removed":
        from app.models.course import CourseMember
        from sqlalchemy import select
        member = db.scalar(select(CourseMember).where(CourseMember.user_id == student.id))
        db.delete(member)
        db.commit()
    def resolve():
        raise AssertionError("provider must not resolve")
    app.dependency_overrides[get_question_embedder] = resolve
    login_as(client, student.username, "pass")
    if blocked == "anonymous":
        client.cookies.clear()
    assert client.post(f"/courses/{course.id}/insights/groups", json={
        "min_similarity": 0.9, "confirm_external_processing": True,
    }).status_code == (401 if blocked == "anonymous" else 403)


def test_grouping_upstream_timeout_returns_no_partial_groups(client, db, context):
    course, user = context
    for query in ["第一问", "第二问"]:
        add_question(db, course, user, query)
    db.commit()
    embedder = Mock()
    embedder.embed.side_effect = UpstreamTimeout("private question/provider secret")
    app.dependency_overrides[get_question_embedder] = lambda: embedder
    response = client.post(f"/courses/{course.id}/insights/groups", json={
        "min_similarity": 0.9, "confirm_external_processing": True,
    })
    assert response.status_code == 504
    assert response.json()["error_code"] == "UPSTREAM_TIMEOUT"
    assert "groups" not in response.json()
    assert "private" not in response.text


@pytest.mark.parametrize("limit", ["questions", "query", "total"])
def test_resource_limits_fail_before_any_embedding(client, db, context, monkeypatch, limit):
    course, user = context
    queries = ["合成甲", "合成乙", "合成丙"]
    if limit == "questions":
        monkeypatch.setattr("app.services.question_groups.MAX_QUESTIONS", 2)
    elif limit == "query":
        queries[0] = "超" * 2001
    else:
        monkeypatch.setattr("app.services.question_groups.MAX_TOTAL_CHARS", 1)
    for query in queries:
        add_question(db, course, user, query)
    db.commit()
    embedder = Mock()
    app.dependency_overrides[get_question_embedder] = lambda: embedder
    response = client.post(f"/courses/{course.id}/insights/groups", json={
        "min_similarity": 0.9, "confirm_external_processing": True,
    })
    assert response.status_code == 413
    assert response.json()["error_code"] == "QUESTION_GROUPING_LIMIT"
    embedder.embed.assert_not_called()


def test_factory_only_reuses_explicit_real_provider_and_never_calls_it(monkeypatch):
    settings = Settings(_env_file=None, question_grouping_backend="embedding", embedder_backend="siliconflow")
    sentinel = Mock()
    build = Mock(return_value=sentinel)
    monkeypatch.setattr("app.services.question_groups.build_embedder", build)
    assert build_question_embedder(settings) is sentinel
    build.assert_called_once_with(settings)
    sentinel.embed.assert_not_called()
    assert build_question_embedder(Settings(_env_file=None, question_grouping_backend="disabled")) is None


def test_request_scoped_provider_closes_even_on_error(monkeypatch):
    provider = Mock()
    monkeypatch.setattr("app.services.question_groups.build_question_embedder", lambda settings: provider)
    dependency = get_question_embedder(Settings(_env_file=None))
    assert next(dependency) is provider
    with pytest.raises(UpstreamTimeout):
        dependency.throw(UpstreamTimeout())
    provider.close.assert_called_once()


def test_confirmation_and_invalid_window_prevent_embedding(client, db, context):
    course, _ = context
    embedder = Mock()
    app.dependency_overrides[get_question_embedder] = lambda: embedder
    for payload in [
        {"min_similarity": 0.9},
        {"min_similarity": 0.9, "confirm_external_processing": True, "start_at": "2099-01-01T00:00:00Z"},
    ]:
        assert client.post(f"/courses/{course.id}/insights/groups", json=payload).status_code == 422
    embedder.embed.assert_not_called()
