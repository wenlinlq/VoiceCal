import { computed } from 'vue'
import { getMpSafeArea } from '@/utils/mp-safe-area.js'

const metrics = getMpSafeArea()

export function useMpSafeArea() {
  /** 与胶囊同一行的顶栏（左侧放操作按钮） */
  const navRowStyle = computed(() => {
    if (!metrics.isMp) return {}
    return {
      paddingTop: `${metrics.statusBarHeight}px`,
      height: `${metrics.navRowHeight}px`,
      boxSizing: 'border-box',
    }
  })

  /** 底部麦克风按钮 */
  const micWrapStyle = computed(() => {
    if (!metrics.isMp) return {}
    return {
      bottom: `calc(40rpx + ${metrics.safeBottom}px)`,
    }
  })

  /** 带底部麦克风的页面留白 */
  const pageBottomStyle = computed(() => {
    if (!metrics.isMp) return {}
    return {
      paddingBottom: `calc(180rpx + ${metrics.safeBottom}px)`,
    }
  })

  /** 带返回按钮的 custom 导航栏 */
  const navBarStyle = computed(() => {
    if (!metrics.isMp) return {}
    return {
      paddingTop: `${metrics.safeTop}px`,
    }
  })

  return {
    metrics,
    navRowStyle,
    micWrapStyle,
    pageBottomStyle,
    navBarStyle,
  }
}
