<script setup>
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useUserStore } from "@/store/modules/user.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { checkHealth } from "@/api/health.js";
import {
  isMpWeixin,
  logWechatAuthContext,
} from "@/utils/wechat-login.js";

onLaunch(async () => {
  console.log("语音日历 App Launch");
  logWechatAuthContext("[前端启动] 微信登录上下文");

  const calendarStore = useCalendarStore();
  const userStore = useUserStore();
  userStore.restoreFromCache();

  try {
    const health = await checkHealth();
    console.log("[后端] 健康检查通过", health);
  } catch (error) {
    console.warn("[后端] 健康检查失败", error);
  }

  try {
    const loginInfo = await userStore.ensureAuth();
    console.log(
      isMpWeixin() ? "[微信登录] 成功" : "[开发登录] 成功",
      loginInfo.openid,
    );
  } catch (error) {
    userStore.setLoginError(error?.message || String(error));
    console.error("[登录] 失败：", error);
    logWechatAuthContext("[登录失败] 当前上下文");
    uni.showToast({ title: "登录失败", icon: "none" });
  }

  if (!userStore.token) {
    console.warn("[后端] 未登录，跳过日程加载");
    return;
  }

  try {
    await calendarStore.fetchEvents();
    console.log("[后端] 日程加载成功", calendarStore.events.length);
  } catch (error) {
    uni.showToast({ title: "日程加载失败", icon: "none" });
    console.error("[后端] 日程加载失败", error);
  }
});

onShow(() => {
  console.log("App Show");
});

onHide(() => {
  console.log("App Hide");
});
</script>

<style lang="scss">
page {
  background-color: #ffffff;
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
    Arial, sans-serif;
  color: #333;
  box-sizing: border-box;
}

view,
text {
  box-sizing: border-box;
}
</style>
