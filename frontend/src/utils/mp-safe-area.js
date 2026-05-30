/**
 * 微信小程序安全区与胶囊按钮避让尺寸（px）
 * 用于 custom 导航栏页面
 */
export function getMpSafeArea() {
  const fallback = {
    isMp: false,
    statusBarHeight: 0,
    navBarHeight: 44,
    safeTop: 0,
    safeBottom: 0,
    capsuleRight: 0,
    navRowHeight: 0,
  }

  // #ifdef MP-WEIXIN
  try {
    const windowInfo = typeof uni.getWindowInfo === 'function'
      ? uni.getWindowInfo()
      : uni.getSystemInfoSync()
    const menu = uni.getMenuButtonBoundingClientRect()
    const statusBarHeight = windowInfo.statusBarHeight || 0
    const navBarHeight = (menu.top - statusBarHeight) * 2 + menu.height
    const safeTop = menu.bottom + 8
    const safeBottom =
      windowInfo.safeAreaInsets?.bottom ??
      (windowInfo.safeArea
        ? Math.max(windowInfo.screenHeight - windowInfo.safeArea.bottom, 0)
        : 0)
    const capsuleRight = Math.max(windowInfo.windowWidth - menu.left + 10, 16)

    return {
      isMp: true,
      statusBarHeight,
      navBarHeight,
      safeTop,
      safeBottom,
      capsuleRight,
      navRowHeight: safeTop,
    }
  } catch (e) {
    console.warn('[mp-safe-area] fallback', e)
    return {
      isMp: true,
      statusBarHeight: 44,
      navBarHeight: 44,
      safeTop: 88,
      safeBottom: 34,
      capsuleRight: 100,
      navRowHeight: 88,
    }
  }
  // #endif

  // #ifndef MP-WEIXIN
  return fallback
  // #endif
}
