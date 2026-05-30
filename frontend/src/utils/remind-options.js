import { formatDateTimeValue, parseDateTime } from "@/utils/date.js";

/** 提前提醒可选时长（分钟） */
export const REMIND_BEFORE_OPTIONS = [
  { value: 5, label: "提前 5 分钟" },
  { value: 15, label: "提前 15 分钟" },
  { value: 30, label: "提前 30 分钟" },
  { value: 60, label: "提前 1 小时" },
  { value: 120, label: "提前 2 小时" },
  { value: 360, label: "提前 6 小时" },
  { value: 1440, label: "提前 1 天" },
  { value: 2880, label: "提前 2 天" },
];

export const DEFAULT_REMIND_BEFORE_MINUTES = 30;

export function getRemindBeforeLabel(minutes) {
  const opt = REMIND_BEFORE_OPTIONS.find((o) => o.value === minutes);
  return opt?.label || `提前 ${minutes} 分钟`;
}

/** 根据开始时间与提前分钟数计算 remind_at */
export function computeRemindAt(startTimeStr, minutesBefore = DEFAULT_REMIND_BEFORE_MINUTES) {
  const start = parseDateTime(startTimeStr);
  start.setMinutes(start.getMinutes() - Number(minutesBefore));
  return formatDateTimeValue(start);
}

/** 从已有 remind_at 反推最接近的选项（编辑回填） */
export function inferRemindBeforeMinutes(startTimeStr, remindAtStr) {
  if (!startTimeStr || !remindAtStr) {
    return DEFAULT_REMIND_BEFORE_MINUTES;
  }
  const diffMs = parseDateTime(startTimeStr) - parseDateTime(remindAtStr);
  const mins = Math.max(0, Math.round(diffMs / 60000));
  let closest = DEFAULT_REMIND_BEFORE_MINUTES;
  let minDiff = Infinity;
  for (const opt of REMIND_BEFORE_OPTIONS) {
    const d = Math.abs(opt.value - mins);
    if (d < minDiff) {
      minDiff = d;
      closest = opt.value;
    }
  }
  return closest;
}
