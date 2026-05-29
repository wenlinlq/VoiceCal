import { defineConfig, loadEnv } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import fs from "node:fs";
import path from "node:path";

const manifestPath = path.resolve(__dirname, "src/manifest.json");

function patchMpWeixinAppId(appId) {
  let originalContent = null;

  function apply() {
    const content = fs.readFileSync(manifestPath, "utf-8");
    if (originalContent === null) {
      originalContent = content;
    }
    const next = content.replace(
      /("mp-weixin"\s*:\s*\{[\s\S]*?"appid"\s*:\s*)"[^"]*"/,
      `$1"${appId || ""}"`,
    );
    fs.writeFileSync(manifestPath, next);
  }

  function restore() {
    if (originalContent !== null) {
      fs.writeFileSync(manifestPath, originalContent);
      originalContent = null;
    }
  }

  let restored = false;
  function restoreOnce() {
    if (restored) return;
    restored = true;
    restore();
  }

  return {
    name: "inject-mp-weixin-appid",
    enforce: "pre",
    config() {
      apply();
      if (!appId) {
        console.warn(
          "[vite] 未配置 VITE_MP_WEIXIN_APPID，请复制 .env.example 为 .env.local 并填写微信小程序 AppID",
        );
      }
      process.on("exit", restoreOnce);
      process.on("SIGINT", () => {
        restoreOnce();
        process.exit();
      });
    },
    closeBundle: restoreOnce,
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const mpWeixinAppId = env.VITE_MP_WEIXIN_APPID || "";

  return {
    plugins: [patchMpWeixinAppId(mpWeixinAppId), uni()],
  };
});
