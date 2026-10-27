"""College CRUD, nullable affiliations and unchanged course authorization."""

from uuid import UUID, uuid4

import pytest
from app.models import College, CourseMember

from tests import test_course_business as business

client = business.client
scope = business.scope
login = business.login


def create_college(client, code="CS", name="计算机学院"):
    response = client.post("/admin/colleges", json={"code": code, "name": name})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("role", [None, "teacher", "student"])
def test_college_maintenance_admin_only(client, scope, role):
    if role:
        login(client, role)
    expected = 403 if role else 401
    body = {"code": "CS", "name": "计算机学院"}
    assert client.get("/admin/colleges").status_code == expected
    assert client.post("/admin/colleges", json=body).status_code == expected
    assert client.put(f"/admin/colleges/{uuid4()}", json=body).status_code == expected
    assert client.delete(f"/admin/colleges/{uuid4()}").status_code == expected


def test_college_crud_conflicts_and_missing_rows(client, scope):
    login(client, "admin")
    first = create_college(client, " CS ", " 计算机学院 ")
    assert first["code"] == "CS" and first["name"] == "计算机学院"
    second = create_college(client, "EE", "计算机学院")  # Only code is unique.
    path = f"/admin/colleges/{first['id']}"
    assert len(client.get("/admin/colleges").json()) == 2
    assert client.post("/admin/colleges", json={"code": "CS", "name": "冲突"}).status_code == 409
    assert client.put(path, json={"code": "EE", "name": "必须回滚"}).status_code == 409
    row = next(c for c in client.get("/admin/colleges").json() if c["id"] == first["id"])
    assert row == first
    response = client.put(path, json={"code": "CSE", "name": "计算机与软件学院"})
    assert response.status_code == 200
    assert response.json()["name"] == "计算机与软件学院"
    assert client.delete(path).status_code == 204
    assert client.delete(path).status_code == 404
    assert client.put(path, json={"code": "CS", "name": "无记录"}).status_code == 404
    assert client.delete(f"/admin/colleges/{second['id']}").status_code == 204


@pytest.mark.parametrize("body", [
    {"code": "", "name": "学院"}, {"code": "   ", "name": "学院"},
    {"code": "bad code", "name": "学院"}, {"code": "x" * 65, "name": "学院"},
    {"code": "CS", "name": "   "}, {"code": "CS", "name": "x" * 101},
    {"code": None, "name": "学院"}, {"code": "CS", "name": None},
    {"name": "学院"}, {"code": "CS"},
])
def test_college_validation_on_create_and_update(client, scope, body):
    login(client, "admin")
    row = create_college(client)
    assert client.post("/admin/colleges", json=body).status_code == 422
    assert client.put(f"/admin/colleges/{row['id']}", json=body).status_code == 422


def test_course_affiliation_creation_patch_clear_and_mounted_delete(client, scope):
    login(client, "admin")
    college = create_college(client)
    cid = college["id"]
    response = client.post("/admin/courses", json={"title": "新课", "college_id": cid})
    assert response.status_code == 201
    row = response.json()
    assert (row["college_id"], row["college_name"]) == (cid, college["name"])
    path = f"/admin/courses/{row['id']}"
    assert client.patch(path, json={"title": "改课名"}).json()["college_id"] == cid
    assert client.delete(f"/admin/colleges/{cid}").status_code == 409
    listed = next(c for c in client.get("/admin/courses").json() if c["id"] == row["id"])
    assert listed["college_name"] == college["name"]
    assert client.patch(path, json={"college_id": None}).json()["college_name"] is None
    assert client.patch(path, json={"college_id": cid}).json()["college_id"] == cid
    assert client.patch(path, json={"college_id": None}).json()["college_id"] is None
    assert client.delete(f"/admin/colleges/{cid}").status_code == 204
    plain = client.post("/admin/courses", json={"title": "无学院"}).json()
    assert plain["college_id"] is None and plain["college_name"] is None


@pytest.mark.parametrize("role", ["student", "teacher", "admin"])
def test_user_affiliation_all_roles_profile_and_auth(client, scope, role):
    login(client, "admin")
    first = create_college(client)
    second = create_college(client, "EE", "电子学院")
    response = client.post("/admin/users", json={
        "username": "new-person", "password": "pass", "role": role,
        "college_id": first["id"],
    })
    assert response.status_code == 201
    user = response.json()
    assert user["college_name"] == first["name"]
    path = f"/admin/users/{user['id']}"
    assert client.delete(f"/admin/colleges/{first['id']}").status_code == 409
    assert client.patch(path, json={"full_name": "姓名"}).json()["college_id"] == first["id"]
    changed = client.patch(path, json={"college_id": second["id"]}).json()
    assert changed["college_id"] == second["id"] and changed["college_name"] == second["name"]
    listed = next(u for u in client.get("/admin/users").json() if u["id"] == user["id"])
    assert listed["college_name"] == second["name"]
    renamed = client.put(f"/admin/colleges/{second['id']}", json={"code": "EE", "name": "电子信息学院"})
    assert renamed.status_code == 200
    login_response = client.post("/auth/login", json={"username": "new-person", "password": "pass"})
    for body in (login_response.json(), client.get("/auth/me").json(), client.get("/auth/profile").json()):
        assert body["college_id"] == second["id"] and body["college_name"] == "电子信息学院"
    login(client, "admin")
    cleared = client.patch(path, json={"college_id": None}).json()
    assert cleared["college_id"] is None and cleared["college_name"] is None
    assert client.delete(f"/admin/colleges/{first['id']}").status_code == 204
    assert client.delete(f"/admin/colleges/{second['id']}").status_code == 204


@pytest.mark.parametrize("college_id,expected", [("invalid", 422), (str(uuid4()), 404)])
def test_invalid_affiliation_rejected_without_partial_update(client, scope, college_id, expected):
    login(client, "admin")
    assert client.post("/admin/courses", json={"title": "invalid", "college_id": college_id}).status_code == expected
    assert client.post("/admin/users", json={
        "username": "invalid", "password": "pass", "role": "student", "college_id": college_id,
    }).status_code == expected
    path = f"/admin/courses/{scope.course.id}"
    assert client.patch(path, json={"college_id": college_id, "title": "should roll back"}).status_code == expected
    row = next(c for c in client.get("/admin/courses").json() if c["id"] == str(scope.course.id))
    assert row["title"] == "测试课程" and row["college_id"] is None
    uid = str(scope.people["student"].id)
    assert client.patch(f"/admin/users/{uid}", json={"college_id": college_id, "full_name": "should roll back"}).status_code == expected
    user = next(u for u in client.get("/admin/users").json() if u["id"] == uid)
    assert user["full_name"] == "张同学" and user["college_id"] is None


def test_college_is_not_a_course_permission_boundary(client, db, scope):
    login(client, "admin")
    first = create_college(client)
    second = create_college(client, "EE", "电子学院")
    for course in (scope.course, scope.other):
        assert client.patch(f"/admin/courses/{course.id}", json={"college_id": first["id"]}).status_code == 200
    assert client.patch(f"/admin/users/{scope.people['student'].id}", json={"college_id": first["id"]}).status_code == 200
    login(client, "student")
    # Same college grants no membership, including search access.
    assert client.get("/courses").json() == []
    root = f"/courses/{scope.course.id}"
    assert client.get(root).status_code == 403
    assert client.post(root + "/search", json={"query": "测试"}).status_code == 403
    db.add(CourseMember(course_id=scope.course.id, user_id=scope.people["student"].id, role="student"))
    db.commit()
    login(client, "admin")
    assert client.patch(f"/admin/users/{scope.people['student'].id}", json={"college_id": second["id"]}).status_code == 200
    login(client, "student")
    # A different college cannot revoke existing course access or add other courses.
    courses = client.get("/courses").json()
    assert [c["id"] for c in courses] == [str(scope.course.id)]
    assert courses[0]["college_name"] == first["name"]
    assert client.get(root).json()["college_id"] == first["id"]
    assert client.get(f"/courses/{scope.other.id}").status_code == 403
    assert db.get(College, UUID(second["id"])) is not None
