/**
 * 跨端 requestAnimationFrame
 * H5 使用浏览器原生实现，小程序用 setTimeout 模拟
 * @param {FrameRequestCallback} callback
 * @returns {number}
 */
export function raf(callback) {
  if (typeof requestAnimationFrame === "function") {
    return requestAnimationFrame(callback);
  }
  return setTimeout(() => callback(Date.now()), 16);
}

/**
 * 连续两帧后执行，确保 DOM / 样式更新后再触发动画
 * @param {FrameRequestCallback} callback
 */
export function rafTwice(callback) {
  raf(() => raf(callback));
}
