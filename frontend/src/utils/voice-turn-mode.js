/** 增删改完成语（对齐后端 Agent 完成关键词） */
const WRITE_DONE_RE =
  /已(?:为你|经)?(?:创建|添加|删除|修改|设置|安排|取消)|帮你(?:安排|设置)/;

/** 查询类回复常见表述 */
const QUERY_REPLY_RE =
  /(?:有什么|哪些|几(?:个|条)|查(?:到|询)|共有|暂无|没有(?:安排|日程|会议)|以下)/;

const QUERY_DATE_RE = /今天|明天|后天|本周|下周/;

/**
 * 纯前端推断本轮 WS 会话策略（不依赖后端 turn_mode 字段）
 * @returns {"write_done"|"query"|"continue"}
 */
export function resolveVoiceTurnMode(replyText, needConfirm = false) {
  if (needConfirm) return "continue";

  const text = (replyText || "").trim();
  if (!text) return "continue";

  if (/[？?]/.test(text)) return "continue";

  if (WRITE_DONE_RE.test(text)) return "write_done";

  if (
    QUERY_REPLY_RE.test(text) ||
    (QUERY_DATE_RE.test(text) && /安排|日程|会议|事项/.test(text))
  ) {
    return "query";
  }

  return "continue";
}
