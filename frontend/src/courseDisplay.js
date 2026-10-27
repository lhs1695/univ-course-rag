// Stable sort keeps the server's relative order within each priority group.
export function sortCoursesForDisplay(courses) {
  const priority = course => {
    if (course.title?.includes("机器学习")) return 0;
    if (course.title?.includes("智能移动机器人")) return 1;
    return 2;
  };
  return [...courses].sort((a, b) => priority(a) - priority(b));
}
