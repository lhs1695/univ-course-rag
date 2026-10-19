import { askHistory } from './askHistory.js';

// Questions stay in memory only, scoped to the signed-in user and course.
let ownerId = null;
const questions = new Map();
export function questionDraft(userId, courseId, value) {
  if (ownerId !== userId) {
    questions.clear();
    ownerId = userId;
  }
  if (value !== undefined) questions.set(courseId, value);
  return questions.get(courseId) || "";
}
export function clearDrafts() {
  askHistory.clear();
  questions.clear();
  ownerId = null;
}
