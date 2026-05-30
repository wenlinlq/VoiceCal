import { reportSubscribeResult } from "@/api/wechat.js";
import { SUBSCRIBE_TEMPLATE_ID } from "@/config/api.js";
import { getAuthToken } from "@/utils/auth.js";
import { isMpWeixin } from "@/utils/wechat-login.js";
import { parseDateTime } from "@/utils/date.js";
import {
  computeRemindAt,
  DEFAULT_REMIND_BEFORE_MINUTES,
} from "@/utils/remind-options.js";

/** 将 wx.requestSubscribeMessage 返回值映射为后端 status */
export function mapWxSubscribeStatus(wxStatus) {
  if (wxStatus === "accept") return "accept";
  if (wxStatus === "ban") return "ban";
  return "reject";
}

/** 从微信回调对象中解析指定模板的授权结果 */
export function extractWxSubscribeStatus(res, templateId) {
  if (!res || !templateId) return "reject";

  const direct = res[templateId];
  if (direct) return mapWxSubscribeStatus(direct);

  for (const key of Object.keys(res)) {
    if (key === "errMsg" || key === "errCode") continue;
    if (key === templateId) {
      return mapWxSubscribeStatus(res[key]);
    }
  }

  return "reject";
}

/**
 * 调起微信订阅授权并上报后端 POST /api/wechat/subscribe-result
 */
export function requestSubscribeAndReport(templateId = SUBSCRIBE_TEMPLATE_ID) {
  if (!isMpWeixin()) {
    return Promise.resolve({
      accepted: false,
      status: "reject",
      templateId: templateId || "",
      skipped: true,
    });
  }

  if (!templateId) {
    return Promise.reject(new Error("未配置订阅消息模板 ID"));
  }

  if (!getAuthToken()) {
    return Promise.reject(new Error("请先登录后再开启提醒"));
  }

  return new Promise((resolve, reject) => {
    uni.requestSubscribeMessage({
      tmplIds: [templateId],
      success: async (res) => {
        const status = extractWxSubscribeStatus(res, templateId);
        try {
          await reportSubscribeResult({
            template_id: templateId,
            status,
          });
          resolve({
            accepted: status === "accept",
            status,
            templateId,
          });
        } catch (err) {
          reject(
            new Error(err?.message || "订阅状态上报失败，请检查网络与登录状态"),
          );
        }
      },
      fail: async (err) => {
        const msg = err?.errMsg || "订阅授权失败";
        if (msg.includes("cancel")) {
          try {
            await reportSubscribeResult({
              template_id: templateId,
              status: "reject",
            });
          } catch (_) {
            /* 上报失败不阻断 */
          }
          resolve({
            accepted: false,
            status: "reject",
            templateId,
            cancelled: true,
          });
          return;
        }
        reject(new Error(msg));
      },
    });
  });
}

/**
 * 保存日程前：若开启提醒则走订阅授权，并补齐 remind / template 字段
 */
export async function prepareEventForSave(formData) {
  const result = { ...formData };

  if (!result.remind_enabled) {
    result.remind_enabled = false;
    return result;
  }

  if (!SUBSCRIBE_TEMPLATE_ID) {
    uni.showToast({
      title: "请在 .env.local 配置 VITE_WECHAT_SUBSCRIBE_TEMPLATE_ID",
      icon: "none",
      duration: 3000,
    });
    result.remind_enabled = false;
    return result;
  }

  if (!isMpWeixin()) {
    uni.showToast({ title: "仅微信小程序支持订阅提醒", icon: "none" });
    result.remind_enabled = false;
    return result;
  }

  const minutesBefore =
    result.remind_before_minutes ?? DEFAULT_REMIND_BEFORE_MINUTES;
  result.remind_at = computeRemindAt(result.start_time, minutesBefore);
  result.subscribe_template_id = SUBSCRIBE_TEMPLATE_ID;

  if (parseDateTime(result.remind_at) <= new Date()) {
    uni.showToast({
      title: "提醒时间已过，请把日程开始时间设晚一些",
      icon: "none",
    });
    result.remind_enabled = false;
    delete result.subscribe_template_id;
    delete result.remind_at;
    return result;
  }

  const sub = await requestSubscribeAndReport(SUBSCRIBE_TEMPLATE_ID);

  if (!sub.accepted) {
    result.remind_enabled = false;
    delete result.subscribe_template_id;
    delete result.remind_at;
    if (!sub.cancelled) {
      uni.showToast({
        title: "需同意订阅消息才能开启提醒",
        icon: "none",
      });
    }
    return result;
  }

  return result;
}

/** 设置页单独重新授权订阅 */
export async function promptSubscribeMessage() {
  if (!isMpWeixin()) {
    uni.showToast({ title: "仅微信小程序可用", icon: "none" });
    return;
  }
  if (!SUBSCRIBE_TEMPLATE_ID) {
    uni.showToast({
      title: "未配置 VITE_WECHAT_SUBSCRIBE_TEMPLATE_ID",
      icon: "none",
    });
    return;
  }

  try {
    const sub = await requestSubscribeAndReport(SUBSCRIBE_TEMPLATE_ID);
    if (sub.accepted) {
      uni.showToast({ title: "订阅已授权并上报", icon: "success" });
    } else if (sub.cancelled) {
      uni.showToast({ title: "已取消", icon: "none" });
    } else {
      uni.showToast({ title: "未同意订阅", icon: "none" });
    }
  } catch (err) {
    uni.showToast({ title: err.message || "订阅失败", icon: "none" });
  }
}

/** 创建/更新成功后的提示文案 */
export function getRemindSuccessHint(event) {
  if (!event?.remind_enabled || !event?.remind_at) return "";
  const at = String(event.remind_at).slice(0, 16).replace("T", " ");
  return `，将在 ${at} 提醒`;
}
