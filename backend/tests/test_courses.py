from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.user import User, UserRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import add_user


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
