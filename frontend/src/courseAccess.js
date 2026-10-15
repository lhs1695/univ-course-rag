import { reactive } from "vue";
import { api } from "./api.js";

export const courseAccess = reactive({ course: null, revision: 0, error: null });
let requestVersion = 0;

export function clearCourseAccess() {
  requestVersion += 1;
  courseAccess.course = null;
  courseAccess.error = null;
  courseAccess.revision += 1;
}

export async function refreshCourseAccess(courseId) {
  const version = ++requestVersion;
  const previous = courseAccess.course;
  let course;
  try {
    course = await api(`/courses/${courseId}`);
  } catch (error) {
    if (version === requestVersion || [401, 403, 404].includes(error.status)) {
      courseAccess.error = error;
    }
    throw error;
  }
  if (version !== requestVersion) return null;
  if (previous?.id !== course.id || previous?.membership_role !== course.membership_role) {
    courseAccess.revision += 1;
  }
  courseAccess.course = course;
  courseAccess.error = null;
  return course;
}

window.addEventListener("access-denied", ({ detail }) => {
  if (detail.status === 401 || detail.courseId === courseAccess.course?.id) {
    clearCourseAccess();
  }
});
