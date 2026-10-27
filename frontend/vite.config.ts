/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  // Vite uses 5173 and silently moves to 5174, 5175 ... if that port is busy. The backend accepts any
  // localhost/127.0.0.1 port while ENVIRONMENT=development, so either port works with CORS.
  server: { port: 5173 },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"], css: false },
});
