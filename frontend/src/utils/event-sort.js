/**
 * 日程列表排序（前端）：未完成在前，已完成在后；同组内按开始时间升序
 * 与 api(1).md GET /api/events 说明一致
 */
export function compareEvents(a, b) {
  const aDone = a.completed ? 1 : 0;
  const bDone = b.completed ? 1 : 0;
  if (aDone !== bDone) return aDone - bDone;
  return String(a.start_time).localeCompare(String(b.start_time));
}

export function sortEvents(events) {
  return [...events].sort(compareEvents);
}
