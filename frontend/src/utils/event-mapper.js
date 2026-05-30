import { SUBSCRIBE_TEMPLATE_ID } from "@/config/api.js";
import {
  computeRemindAt,
  DEFAULT_REMIND_BEFORE_MINUTES,
} from "@/utils/remind-options.js";

/** 前端时间 "YYYY-MM-DD HH:mm:ss" → API ISO 8601（带 +08:00） */
export function toApiDateTime(str) {
  if (!str) return str;
  if (str.includes("T")) return str;
  return `${str.replace(" ", "T")}+08:00`;
}

/** 提醒时间：与后端落库一致，使用无时区本地时间字符串 */
export function toApiDateTimeNaive(str) {
  if (!str) return null;
  const normalized = String(str)
    .replace("T", " ")
    .replace(/(\.\d+)?(Z|[+-]\d{2}:\d{2})$/, "")
    .slice(0, 19);
  return normalized.replace(" ", "T");
}

/** API 时间 → 前端 "YYYY-MM-DD HH:mm:ss" */
export function fromApiDateTime(str) {
  if (!str) return "";
  return String(str)
    .replace("T", " ")
    .replace(/(\.\d+)?(Z|[+-]\d{2}:\d{2})$/, "")
    .slice(0, 19);
}

/** 后端 EventResponse → 前端 Event */
export function normalizeEvent(raw) {
  return {
    id: raw.id,
    title: raw.title,
    start_time: fromApiDateTime(raw.start_time),
    end_time: fromApiDateTime(raw.end_time),
    note: raw.description || "",
    location: raw.location || "",
    is_all_day: Boolean(raw.is_all_day),
    repeat_type: "none",
    completed: Boolean(raw.completed),
    remind_enabled: Boolean(raw.remind_enabled),
    remind_at: fromApiDateTime(raw.remind_at),
    subscribe_template_id: raw.subscribe_template_id || "",
    push_status: raw.push_status || "",
  };
}

function applyRemindFields(payload, event) {
  if (!event.remind_enabled) {
    if (event.remind_enabled === false) {
      payload.remind_enabled = false;
    }
    return;
  }

  const minutesBefore =
    event.remind_before_minutes ?? DEFAULT_REMIND_BEFORE_MINUTES;
  const remindAt =
    event.remind_at || computeRemindAt(event.start_time, minutesBefore);
  const templateId = event.subscribe_template_id || SUBSCRIBE_TEMPLATE_ID;

  payload.remind_enabled = true;
  payload.remind_at = toApiDateTimeNaive(remindAt);
  if (templateId) {
    payload.subscribe_template_id = templateId;
  }
}

/** 前端表单 → 后端 EventCreate / EventUpdate */
export function toApiEventPayload(event) {
  const payload = {
    title: event.title,
    description: event.note || null,
    location: event.location || null,
    start_time: toApiDateTime(event.start_time),
    end_time: toApiDateTime(event.end_time),
    is_all_day: Boolean(event.is_all_day),
  };

  if (event.completed !== undefined) {
    payload.completed = Boolean(event.completed);
  }

  applyRemindFields(payload, event);

  if (event.title === undefined) delete payload.title;
  if (event.note === undefined) delete payload.description;

  return payload;
}
