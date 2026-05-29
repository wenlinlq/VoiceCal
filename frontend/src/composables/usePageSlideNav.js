import { ref } from "vue";
import { onShow, onBackPress } from "@dcloudio/uni-app";
import { rafTwice } from "@/utils/raf.js";

const ANIM_DURATION = 320;

/**
 * 子页面右滑进入 / 返回滑出；从子页返回时不重播进入动画
 * @param {{ getFallbackUrl?: () => string }} options
 */
export function usePageSlideNav(options = {}) {
  const pageActive = ref(false);
  const pageLeaving = ref(false);
  let isNavigatingBack = false;
  let hasEntered = false;
  let allowNavigateBack = false;

  function playEnter() {
    rafTwice(() => {
      pageActive.value = true;
      hasEntered = true;
    });
  }

  function resetNavState() {
    pageLeaving.value = false;
    isNavigatingBack = false;
    pageActive.value = true;
  }

  onShow(() => {
    if (hasEntered) {
      resetNavState();
    } else {
      playEnter();
    }
  });

  onBackPress(() => {
    if (allowNavigateBack) {
      return false;
    }
    goBack();
    return true;
  });

  function finishNavigateBack() {
    allowNavigateBack = false;
  }

  function navigateBackOrFallback() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      allowNavigateBack = true;
      uni.navigateBack({
        delta: 1,
        complete: finishNavigateBack,
        fail: () => {
          finishNavigateBack();
          redirectToFallback();
        },
      });
      return;
    }

    redirectToFallback();
  }

  function redirectToFallback() {
    const fallback = options.getFallbackUrl?.();
    if (fallback) {
      uni.redirectTo({ url: fallback });
      return;
    }

    uni.reLaunch({ url: "/pages/index/index" });
  }

  function goBack() {
    if (isNavigatingBack) return;
    isNavigatingBack = true;
    pageLeaving.value = true;
    pageActive.value = false;

    setTimeout(() => {
      navigateBackOrFallback();
    }, ANIM_DURATION);
  }

  return {
    pageActive,
    pageLeaving,
    goBack,
    ANIM_DURATION,
  };
}
