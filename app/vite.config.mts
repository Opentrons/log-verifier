import path from "path"

import react from "@vitejs/plugin-react"
import postCssImport from "postcss-import"
import postCssPresetEnv from "postcss-preset-env"
import type { UserConfig, Plugin } from "vite"
import { defineConfig } from "vite"

export const cssModuleSideEffect = (): Plugin => {
  return {
    name: "css-module-side-effectful",
    enforce: "post",
    transform(_: string, id: string) {
      if (id.includes(".module.")) {
        return {
          moduleSideEffects: "no-treeshake", // or true, which also works with slightly better treeshake
        }
      }
    },
  }
}

export default defineConfig(async (): Promise<UserConfig> => {
  return {
    input: {
      main: path.resolve(import.meta.dirname, "index.html"),
      pdf: path.resolve(import.meta.dirname, "pdf.html"),
    },
    base: "",
    build: {
      outDir: "lib",
      sourcemap: true,
    },
    plugins: [react({ include: "**/*.tsx*/" }), cssModuleSideEffect()],
    css: {
      postcss: {
        plugins: [postCssImport({ root: "./src/" }), postCssPresetEnv({ stage: 0 }) as any],
      },
    },
    resolve: {
      alias: { "@": path.resolve("./src/") },
    },
  }
})
