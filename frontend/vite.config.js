import { defineConfig, loadEnv } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import fs from "node:fs";
import path from "node:path";

const manifestPath = path.resolve(__dirname, "src/manifest.json");
const mpAppJsonPath = path.resolve(__dirname, "dist/dev/mp-weixin/app.json");

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

function stripInvalidMpPermissions() {
  return {
    name: "strip-invalid-mp-permissions",
    closeBundle() {
      if (!fs.existsSync(mpAppJsonPath)) return;
      try {
        const raw = fs.readFileSync(mpAppJsonPath, "utf-8");
        const appJson = JSON.parse(raw);
        if (appJson.permission?.["scope.record"]) {
          delete appJson.permission["scope.record"];
          if (!Object.keys(appJson.permission).length) {
            delete appJson.permission;
          }
          fs.writeFileSync(mpAppJsonPath, `${JSON.stringify(appJson, null, 2)}\n`);
        }
      } catch (error) {
        console.warn("[vite] strip invalid mp permissions failed", error);
      }
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const mpWeixinAppId = env.VITE_MP_WEIXIN_APPID || "";
  const apiHost = env.VITE_API_HOST || "latekin.jufu.vip";
  const apiPort = env.VITE_API_PORT || "8000";
  const apiUrl = env.VITE_API_URL || `https://${apiHost}/api`;
  const wsUrl = env.VITE_WS_URL || `wss://${apiHost}/ws/voice`;

  return {
    define: {
      __VOICECAL_API_HOST__: JSON.stringify(apiHost),
      __VOICECAL_API_PORT__: JSON.stringify(apiPort),
      __VOICECAL_API_URL__: JSON.stringify(apiUrl),
      __VOICECAL_WS_URL__: JSON.stringify(wsUrl),
    },
    plugins: [patchMpWeixinAppId(mpWeixinAppId), uni(), stripInvalidMpPermissions()],
  };
});
