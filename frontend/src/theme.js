import { readonly, ref } from "vue";

export const STUDENT_SURFACE_KEY = "univ-course-rag.student-surface";

function browserStorage() {
  try { return globalThis.localStorage; }
  catch { return null; }
}

// A blocked or full browser store must never prevent entering a course.
export function createStudentSurface(storage = browserStorage()) {
  let saved;
  try { saved = storage?.getItem(STUDENT_SURFACE_KEY); }
  catch { /* Use the default for this session. */ }
  const surface = ref(saved === "ask" ? "ask" : "study");
  function select(value) {
    if (!["study", "ask"].includes(value)) return;
    surface.value = value;
    try { storage?.setItem(STUDENT_SURFACE_KEY, value); }
    catch { /* The in-memory selection remains usable. */ }
  }
  return { surface: readonly(surface), select };
}

export const studentSurface = createStudentSurface();
