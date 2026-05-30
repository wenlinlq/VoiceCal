<template>
  <view class="page-settings" :style="pageBottomStyle">
    <view class="settings-group">
      <view class="settings-item" @tap="checkMicPermission">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">麦克风权限</text>
            <text class="item-desc">{{ micStatusText }}</text>
          </view>
        </view>
        <text class="item-arrow">›</text>
      </view>

      <!-- #ifdef MP-WEIXIN -->
      <view class="settings-item" @tap="onSubscribeMessage">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">订阅消息提醒</text>
            <text class="item-desc">{{ subscribeDesc }}</text>
          </view>
        </view>
        <text class="item-arrow">›</text>
      </view>
      <!-- #endif -->

      <!-- #ifndef MP-WEIXIN -->
      <view class="settings-item column">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">H5 开发登录</text>
            <text class="item-desc">{{ h5AuthDesc }}</text>
          </view>
        </view>
        <input
          class="ws-input"
          v-model="devOpenid"
          placeholder="测试 openid，如 oTestUser001"
        />
        <view class="dev-login-btn" @tap="onH5DevLogin">
          <text>获取 Token（dev-login）</text>
        </view>
      </view>
      <!-- #endif -->

      <view class="settings-item" @tap="clearCache">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">清除缓存</text>
            <text class="item-desc">清除本地存储的日程缓存</text>
          </view>
        </view>
        <text class="item-arrow">›</text>
      </view>
    </view>

    <view class="settings-group">
      <view class="settings-item column">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">API 服务器</text>
            <text class="item-desc">{{ apiUrl }}</text>
          </view>
        </view>
      </view>

      <view class="settings-item column">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">WebSocket 服务器</text>
            <text class="item-desc">语音链路地址，可手动覆盖</text>
          </view>
        </view>
        <input
          class="ws-input"
          v-model="wsUrl"
          placeholder="ws://218.244.137.52:8000/ws/voice"
          @blur="saveWsUrl"
        />
      </view>
    </view>

    <view class="settings-group">
      <view class="settings-item" @tap="showGuide">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">使用引导</text>
            <text class="item-desc">语音指令示例</text>
          </view>
        </view>
        <text class="item-arrow">›</text>
      </view>

      <view class="settings-item">
        <view class="item-left">
          <view class="item-info">
            <text class="item-title">关于</text>
            <text class="item-desc">语音日历 v1.0.0</text>
          </view>
        </view>
      </view>
    </view>

    <view class="guide-card">
      <text class="guide-title">语音指令示例</text>
      <view v-for="(item, index) in guideItems" :key="index" class="guide-item">
        <text class="guide-dot">•</text>
        <text class="guide-text">{{ item }}</text>
      </view>
    </view>

    <GlobalVoice />
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { useWebSocketStore } from "@/store/modules/websocket.js";
import { useUserStore } from "@/store/modules/user.js";
import { useCalendarStore } from "@/store/modules/calendar.js";
import { useMpSafeArea } from "@/composables/useMpSafeArea.js";
import { API_BASE_URL, SUBSCRIBE_TEMPLATE_ID } from "@/config/api.js";
import { DEV_OPENID } from "@/utils/wechat-login.js";
import { promptSubscribeMessage } from "@/utils/mp-subscribe-message.js";
import GlobalVoice from "@/components/GlobalVoice/GlobalVoice.vue";

const wsStore = useWebSocketStore();
const userStore = useUserStore();
const calendarStore = useCalendarStore();
const { pageBottomStyle } = useMpSafeArea();
const wsUrl = ref(wsStore.serverUrl);
const apiUrl = API_BASE_URL;
const devOpenid = ref(DEV_OPENID || userStore.openid || "");
const micStatusText = ref("点击检查权限");

const h5AuthDesc = computed(() => {
  if (userStore.token) {
    return `已登录 ${userStore.openid}，Token 已缓存`;
  }
  return "调用 POST /api/auth/dev-login 获取 JWT";
});
const subscribeDesc = SUBSCRIBE_TEMPLATE_ID
  ? "授权后可接收日程开始前的微信提醒"
  : "未配置模板 ID（见 .env.local）";

const guideItems = [
  "「明天下午3点开会」— 添加日程",
  "「今天有什么安排」— 查看今日事件",
  "「删除今天下午3点的会」— 删除事件",
  "「把明天的会改到后天」— 修改事件",
];

function onSubscribeMessage() {
  promptSubscribeMessage();
}

async function onH5DevLogin() {
  const openid = devOpenid.value.trim();
  if (!openid) {
    uni.showToast({ title: "请填写 openid", icon: "none" });
    return;
  }
  try {
    await userStore.loginWithDevOpenid(openid);
    await calendarStore.fetchEvents();
    uni.showToast({ title: "登录成功，Token 已保存", icon: "success" });
  } catch (error) {
    uni.showToast({
      title: error.message || "dev-login 失败",
      icon: "none",
      duration: 3000,
    });
  }
}

function checkMicPermission() {
  // #ifdef MP-WEIXIN
  uni.authorize({
    scope: "scope.record",
    success: () => {
      micStatusText.value = "已授权";
      uni.showToast({ title: "麦克风已授权", icon: "success" });
    },
    fail: () => {
      micStatusText.value = "未授权";
      uni.showModal({
        title: "需要麦克风权限",
        content: "请在设置中开启麦克风权限，以便使用语音功能",
        confirmText: "去设置",
        success: (res) => {
          if (res.confirm) uni.openSetting();
        },
      });
    },
  });
  // #endif
  // #ifdef H5
  micStatusText.value = "H5 需 HTTPS 环境";
  uni.showToast({ title: "H5 环境需 HTTPS", icon: "none" });
  // #endif
  // #ifndef MP-WEIXIN || H5
  micStatusText.value = "请在真机上测试";
  uni.showToast({ title: "请在真机上测试", icon: "none" });
  // #endif
}

function clearCache() {
  uni.showModal({
    title: "清除缓存",
    content: "确定要清除本地缓存吗？",
    success: (res) => {
      if (res.confirm) {
        uni.clearStorageSync();
        uni.showToast({ title: "缓存已清除", icon: "success" });
      }
    },
  });
}

function saveWsUrl() {
  wsStore.setServerUrl(wsUrl.value);
  uni.showToast({ title: "地址已保存", icon: "success" });
}

function showGuide() {
  uni.showModal({
    title: "语音指令示例",
    content: guideItems.join("\n"),
    showCancel: false,
  });
}
</script>

<style lang="scss" scoped>
.page-settings {
  min-height: 100vh;
  background: #fff;
  padding: 24rpx;

  /* #ifndef MP-WEIXIN */
  padding-bottom: calc(180rpx + env(safe-area-inset-bottom));
  /* #endif */
}

.settings-group {
  background: #fff;
  border-radius: 24rpx;
  margin-bottom: 24rpx;
  overflow: hidden;
  box-shadow: 0 4rpx 24rpx rgba(102, 126, 234, 0.06);
}

.settings-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid #f5f5f5;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: #fafafa;
  }

  &.column {
    flex-direction: column;
    align-items: stretch;
    gap: 16rpx;
  }
}

.item-left {
  display: flex;
  align-items: center;
  gap: 20rpx;
  flex: 1;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.item-title {
  font-size: 28rpx;
  color: #333;
  font-weight: 500;
}

.item-desc {
  font-size: 24rpx;
  color: #999;
}

.item-arrow {
  font-size: 32rpx;
  color: #ccc;
}

.ws-input {
  width: 100%;
  height: 72rpx;
  background: #f5f7fa;
  border-radius: 12rpx;
  padding: 0 20rpx;
  font-size: 26rpx;
  color: #333;
}

.dev-login-btn {
  margin-top: 16rpx;
  height: 72rpx;
  background: #1a73e8;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  text {
    color: #fff;
    font-size: 28rpx;
    font-weight: 500;
  }

  &:active {
    opacity: 0.85;
  }
}

.guide-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 32rpx;
  box-shadow: 0 4rpx 24rpx rgba(102, 126, 234, 0.06);
}

.guide-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 20rpx;
}

.guide-item {
  display: flex;
  align-items: flex-start;
  gap: 8rpx;
  margin-bottom: 12rpx;
}

.guide-dot {
  color: #1a73e8;
  font-size: 28rpx;
  line-height: 1.6;
}

.guide-text {
  font-size: 26rpx;
  color: #666;
  line-height: 1.6;
  flex: 1;
}
</style>
