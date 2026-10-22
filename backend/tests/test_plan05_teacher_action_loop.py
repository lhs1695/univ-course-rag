
"""PLAN-05: teacher insight review persistence and permissions."""

from app.models.course import CourseMemberRole
from app.models.user import UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user
from tests.test_courses import add_course, add_member, login_as


def test_plan05_teacher_can_create_list_and_update_review(client: TestClient, db: Session):
    teacher = add_user(db, "p05-t", "pass", UserRole.teacher)
    course = add_course(db, "P05 Course")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, teacher.username, "pass")
    created = client.post(
        f"/courses/{course.id}/insight-reviews",
        json={
            "subject_type": "clue",
            "subject_key": "什么是向量",
            "intent_code": "concept",
            "knowledge_point": "线性代数/向量",
            "review_status": "confirmed",
            "cause_code": "normal_review",
            "action_code": "clarify_in_class",
            "note": "课堂再讲一遍",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["review_status"] == "confirmed"
    assert body["knowledge_point"] == "线性代数/向量"
    assert body["teacher_id"] == str(teacher.id)
    listed = client.get(f"/courses/{course.id}/insight-reviews")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    updated = client.patch(
        f"/courses/{course.id}/insight-reviews/{body['id']}",
        json={"action_code": "add_regression", "review_status": "confirmed"},
    )
    assert updated.status_code == 200
    assert updated.json()["action_code"] == "add_regression"


def test_plan05_student_and_cross_course_denied(client: TestClient, db: Session):
    teacher = add_user(db, "p05-t2", "pass", UserRole.teacher)
    student = add_user(db, "p05-s", "pass", UserRole.student)
    other = add_user(db, "p05-t3", "pass", UserRole.teacher)
    c1 = add_course(db, "P05 A")
    c2 = add_course(db, "P05 B")
    add_member(db, c1, teacher, CourseMemberRole.teacher)
    add_member(db, c1, student, CourseMemberRole.student)
    add_member(db, c2, other, CourseMemberRole.teacher)
    login_as(client, student.username, "pass")
    assert client.get(f"/courses/{c1.id}/insight-reviews").status_code == 403
    assert client.post(
        f"/courses/{c1.id}/insight-reviews",
        json={"subject_type": "clue", "subject_key": "x", "review_status": "deferred"},
    ).status_code == 403
    login_as(client, other.username, "pass")
    assert client.get(f"/courses/{c1.id}/insight-reviews").status_code == 403
