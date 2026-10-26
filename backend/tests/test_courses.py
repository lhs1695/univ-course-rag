from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.document import Document
from app.models.user import User, UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user, enable_retrieval


def login_as(client: TestClient, username: str, password: str) -> None:
    client.post("/auth/logout")
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def add_course(db: Session, title: str) -> Course:
    course = Course(title=title)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def add_member(db: Session, course: Course, user: User, role: CourseMemberRole) -> None:
    db.add(CourseMember(course_id=course.id, user_id=user.id, role=role.value))
    db.commit()


def test_student_cannot_access_other_course(client: TestClient, db: Session) -> None:
    student_a = add_user(db, "alice", "pass", UserRole.student)
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course1 = add_course(db, "Course 1")
    course2 = add_course(db, "Course 2")
    add_member(db, course1, teacher, CourseMemberRole.teacher)
    add_member(db, course1, student_a, CourseMemberRole.student)
    add_member(db, course2, teacher, CourseMemberRole.teacher)

    login_as(client, "alice", "pass")
    own = client.get(f"/courses/{course1.id}")
    assert own.status_code == 200
    assert own.json()["title"] == "Course 1"
    other = client.get(f"/courses/{course2.id}")
    assert other.status_code == 403
    other_members = client.get(f"/courses/{course2.id}/members")
    assert other_members.status_code == 403
    listed = client.get("/courses")
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert str(course1.id) in ids
    assert str(course2.id) not in ids


def test_student_cannot_change_members(client: TestClient, db: Session) -> None:
    student = add_user(db, "alice", "pass", UserRole.student)
    other = add_user(db, "carol", "pass", UserRole.student)
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    add_member(db, course, student, CourseMemberRole.student)

    login_as(client, "alice", "pass")
    add_by_id = client.post(
        f"/courses/{course.id}/members",
        json={"user_id": str(other.id)},
    )
    assert add_by_id.status_code == 403
    add_by_name = client.post(
        f"/courses/{course.id}/members",
        json={"username": "carol"},
    )
    assert add_by_name.status_code == 403
    removed = client.delete(f"/courses/{course.id}/members/{student.id}")
    assert removed.status_code == 403


def test_teacher_adds_student_by_username(client: TestClient, db: Session) -> None:
    student = add_user(db, "bob", "pass", UserRole.student)
    teacher = add_user(db, "t1", "pass", UserRole.teacher)
    course = add_course(db, "Course 1")
    add_member(db, course, teacher, CourseMemberRole.teacher)

    login_as(client, "t1", "pass")
    added = client.post(
        f"/courses/{course.id}/members",
        json={"username": student.username},
    )
    assert added.status_code == 201
    assert added.json()["username"] == "bob"
    assert added.json()["role"] == CourseMemberRole.student.value

    login_as(client, "bob", "pass")
    listed = client.get("/courses")
    assert listed.status_code == 200
    assert str(course.id) in {row["id"] for row in listed.json()}


def test_teacher_cannot_change_other_course_members(client: TestClient, db: Session) -> None:
    student = add_user(db, "bob", "pass", UserRole.student)
    teacher1 = add_user(db, "t1", "pass", UserRole.teacher)
    teacher2 = add_user(db, "t2", "pass", UserRole.teacher)
    course1 = add_course(db, "Course 1")
    course2 = add_course(db, "Course 2")
    add_member(db, course1, teacher1, CourseMemberRole.teacher)
    add_member(db, course2, teacher2, CourseMemberRole.teacher)

    login_as(client, "t1", "pass")
    add_ok = client.post(
        f"/courses/{course1.id}/members",
        json={"user_id": str(student.id)},
    )
    assert add_ok.status_code == 201
    add_other = client.post(
        f"/courses/{course2.id}/members",
        json={"user_id": str(student.id)},
    )
    assert add_other.status_code == 403
    remove_other = client.delete(f"/courses/{course2.id}/members/{student.id}")
    assert remove_other.status_code == 403


def test_unauthenticated_course_is_401(client: TestClient, db: Session) -> None:
    course = add_course(db, "Course 1")
    assert client.get(f"/courses/{course.id}").status_code == 401
    assert client.get("/courses").status_code == 401
from uuid import UUID, uuid4

import pytest


@pytest.mark.parametrize(
    "global_role, course_role",
    [
        (UserRole.student, CourseMemberRole.student),
        (UserRole.teacher, CourseMemberRole.teacher),
        (UserRole.teacher, CourseMemberRole.student),
        (UserRole.teacher, None),
        (UserRole.admin, None),
        (UserRole.admin, CourseMemberRole.student),
        (UserRole.admin, CourseMemberRole.teacher),
    ],
)
def test_course_permissions_with_admin_document_management_exception(
    client: TestClient, db: Session, global_role: UserRole, course_role: CourseMemberRole | None
) -> None:
    owner = add_user(db, "owner", "pass", UserRole.teacher)
    subject = add_user(db, "subject", "pass", global_role)
    course = add_course(db, "Permission matrix")
    add_member(db, course, owner, CourseMemberRole.teacher)
    if course_role is not None:
        add_member(db, course, subject, course_role)
    login_as(client, "owner", "pass")
    uploaded = client.post(
        f"/courses/{course.id}/documents",
        files={"file": ("evidence.txt", b"alpha beta course evidence", "text/plain")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    login_as(client, "subject", "pass")
    prefix = f"/courses/{course.id}"
    member_status = 200 if course_role is not None else 403
    teacher_status = 200 if course_role == CourseMemberRole.teacher else 403
    can_manage_document = global_role == UserRole.admin or teacher_status == 200
    document_list_status = 200 if global_role == UserRole.admin else member_status
    document_read_status = 200 if can_manage_document else (
        404 if course_role is not None else 403
    )

    assert client.get("/auth/me").json()["role"] == global_role.value
    detail = client.get(prefix)
    assert detail.status_code == member_status
    listed = client.get("/courses").json()
    if course_role is not None:
        assert detail.json() == listed[0]
        assert detail.json()["membership_role"] == course_role.value
        assert all(
            value is (course_role == CourseMemberRole.teacher)
            for value in detail.json()["capabilities"].values()
        )
    else:
        assert listed == []
    assert client.get(prefix + "/members").status_code == teacher_status
    assert client.get(prefix + "/insights").status_code == teacher_status
    documents = client.get(prefix + "/documents")
    assert documents.status_code == document_list_status
    if document_list_status == 200:
        assert [row["id"] for row in documents.json()] == (
            [document_id] if can_manage_document else []
        )
    assert client.get(prefix + f"/documents/{document_id}").status_code == document_read_status
    assert client.get(prefix + f"/documents/{document_id}/content").status_code == document_read_status
    assert client.post(prefix + "/search", json={"query": "alpha"}).status_code == member_status
    assert client.post(prefix + "/ask", json={"query": "alpha"}).status_code == member_status
    uploaded = client.post(
        prefix + "/documents",
        files={"file": ("second.txt", b"more synthetic evidence", "text/plain")},
    )
    assert uploaded.status_code == (201 if teacher_status == 200 else 403)
    # A teacher reaches document lookup; everyone else is rejected before it.
    assert client.post(prefix + f"/documents/{uuid4()}/retry").status_code == (
        404 if teacher_status == 200 else 403
    )
    enable_retrieval(db, document_id)
    assert client.delete(prefix + f"/documents/{document_id}").status_code == (
        204 if can_manage_document else 403
    )
    db.expire_all()
    document = db.get(Document, UUID(document_id))
    assert document is not None
    assert document.retrieval_enabled is (not can_manage_document)


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_admin_explicit_enrollment_and_removal_take_effect_in_same_session(
    client: TestClient, db: Session, role: str
) -> None:
    admin = add_user(db, "admin", "pass", UserRole.admin)
    course = add_course(db, "Explicit enrollment")
    login_as(client, "admin", "pass")
    cookie = client.cookies.get("session_id")
    prefix = f"/courses/{course.id}"
    assert client.get(prefix).status_code == 403
    added = client.post(
        f"/admin/courses/{course.id}/members", json={"user_id": str(admin.id), "role": role}
    )
    assert added.status_code == 201
    assert client.get(prefix).json()["membership_role"] == role
    assert client.get(prefix + "/members").status_code == (200 if role == "teacher" else 403)
    duplicate = client.post(
        f"/admin/courses/{course.id}/members", json={"user_id": str(admin.id), "role": role}
    )
    assert duplicate.status_code == 409
    assert client.delete(f"/admin/courses/{course.id}/members/{admin.id}").status_code == 204
    assert client.cookies.get("session_id") == cookie
    assert client.get(prefix).status_code == 403
    assert client.get(prefix + "/insights").status_code == 403
    assert client.get("/courses").json() == []
    assert client.get("/admin/courses").status_code == 200


def test_removal_and_demotion_recheck_existing_cookie(client: TestClient, db: Session) -> None:
    teacher = add_user(db, "teacher", "pass", UserRole.teacher)
    course = add_course(db, "Role changes")
    add_member(db, course, teacher, CourseMemberRole.teacher)
    login_as(client, "teacher", "pass")
    prefix = f"/courses/{course.id}"
    assert client.get(prefix + "/members").status_code == 200
    member = db.query(CourseMember).filter_by(course_id=course.id, user_id=teacher.id).one()
    member.role = CourseMemberRole.student.value
    db.commit()
    detail = client.get(prefix).json()
    assert detail["membership_role"] == "student"
    assert not any(detail["capabilities"].values())
    assert client.get(prefix + "/members").status_code == 403
    assert client.get(prefix + "/insights").status_code == 403
    db.delete(member)
    db.commit()
    for suffix in ("", "/members", "/documents", "/insights", f"/documents/{uuid4()}/content"):
        assert client.get(prefix + suffix).status_code == 403
    for suffix in ("/ask", "/search"):
        assert client.post(prefix + suffix, json={"query": "alpha"}).status_code == 403


def test_regular_accounts_cannot_assign_members_or_override_account_roles(
    client: TestClient, db: Session
) -> None:
    teacher = add_user(db, "teacher", "pass", UserRole.teacher)
    student = add_user(db, "student", "pass", UserRole.student)
    add_user(db, "admin", "pass", UserRole.admin)
    course = add_course(db, "Assignment rules")
    login_as(client, "teacher", "pass")
    assert client.post(
        f"/admin/courses/{course.id}/members",
        json={"user_id": str(teacher.id), "role": "teacher"},
    ).status_code == 403
    login_as(client, "admin", "pass")
    for user, role in ((student, "teacher"), (teacher, "student")):
        assert client.post(
            f"/admin/courses/{course.id}/members",
            json={"user_id": str(user.id), "role": role},
        ).status_code == 400
