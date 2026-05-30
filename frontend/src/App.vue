<script setup>
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useUserStore } from "@/store/modules/user.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { checkHealth } from "@/api/health.js";
import { isMpWeixin } from "@/utils/wechat-login.js";

onLaunch(async () => {
  console.log("语音日历 App Launch");

  const calendarStore = useCalendarStore();

  try {
    const health = await checkHealth();
    console.log("[后端] 健康检查通过", health);
  } catch (error) {
    console.warn("[后端] 健康检查失败", error);
  }

  try {
    await calendarStore.fetchEvents();
    console.log("[后端] 日程加载成功", calendarStore.events.length);
  } catch (error) {
    uni.showToast({ title: "日程加载失败", icon: "none" });
    console.error("[后端] 日程加载失败", error);
  }

  if (!isMpWeixin()) {
    console.log("[微信静默登录] 非微信小程序环境，跳过");
    return;
  }

  const userStore = useUserStore();
  userStore.restoreFromCache();

  try {
    const loginInfo = await userStore.silentLogin();
    console.log("[微信静默登录] 登录成功，用户信息：", loginInfo);
  } catch (error) {
    userStore.setLoginError(error?.message || String(error));
    console.error("[微信静默登录] 登录失败：", error);
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
