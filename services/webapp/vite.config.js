import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Mismo proxy nginx para ambos prefijos: conserva la autenticación del operador.
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.DEV_PROXY_TARGET || "http://127.0.0.1:3000";
  return { plugins: [react()], server: { proxy: {
    "/api-op": { target },
    "/api": { target },
  } } };
});
