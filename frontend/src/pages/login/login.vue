<template>
  <view class="login-page">
    <view class="login-card">
      <text class="login-title">声历 VoiceCal</text>
      <text class="login-sub">AI 语音日程管家</text>

      <!-- #ifdef H5 -->
      <view class="login-form">
        <button class="login-btn primary" :disabled="loading" @click="loginAs('七牛云老师')">
          {{ loading ? "进入中..." : "🎓 以「七牛云老师」身份进入" }}
        </button>
        <text v-if="error" class="login-error">{{ error }}</text>
      </view>

      <view class="platform-notice">
        <text class="notice-text">
          微信小程序版本正在开发中，因 ICP 备案审核中暂未正式上线。您可先在浏览器中体验完整功能。
        </text>
      </view>
      <!-- #endif -->

      <!-- #ifdef MP-WEIXIN -->
      <button class="login-btn primary" :disabled="loading" @click="doMpLogin">
        {{ loading ? "登录中..." : "微信一键登录" }}
      </button>
      <text v-if="error" class="login-error">{{ error }}</text>
      <!-- #endif -->
    </view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { useUserStore } from "@/store/modules/user.js";
import { devSilentLogin } from "@/utils/wechat-login.js";

const userStore = useUserStore();
const loading = ref(false);
const error = ref("");

async function loginAs(id) {
  loading.value = true;
  error.value = "";
  try {
    await devSilentLogin(id);
    userStore.restoreFromCache();
    uni.reLaunch({ url: "/pages/index/index" });
  } catch (e) {
    error.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}

async function doMpLogin() {
  loading.value = true;
  error.value = "";
  try {
    const info = await userStore.ensureAuth();
    if (info?.token) {
      uni.reLaunch({ url: "/pages/index/index" });
    } else {
      error.value = "登录失败，请重试";
    }
  } catch (e) {
    error.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40rpx;
}

.login-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 60rpx 48rpx;
  width: 100%;
  max-width: 600rpx;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.15);
  text-align: center;
}

.login-title {
  font-size: 52rpx;
  font-weight: 700;
  color: #1a1a1a;
  display: block;
}

.login-sub {
  font-size: 28rpx;
  color: #999;
  display: block;
  margin-top: 12rpx;
  margin-bottom: 48rpx;
}

.login-form {
  text-align: left;
}

.login-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  border-radius: 12rpx;
  padding: 24rpx;
  font-size: 30rpx;
  font-weight: 500;
  margin-bottom: 16rpx;
}

.login-btn.primary {
  font-size: 32rpx;
  padding: 28rpx;
}

.login-btn[disabled] {
  opacity: 0.6;
}

.login-error {
  color: #e74c3c;
  font-size: 24rpx;
  display: block;
  margin-top: 16rpx;
  text-align: center;
}

.platform-notice {
  margin-top: 32rpx;
  padding: 24rpx;
  background: #f5f7ff;
  border-radius: 12rpx;
  border-left: 4rpx solid #667eea;
}

.notice-text {
  font-size: 24rpx;
  color: #888;
  line-height: 1.6;
}
</style>
