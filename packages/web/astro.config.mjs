import { defineConfig } from 'astro/config';
import tailwind from '@tailwindcss/vite';

import { vanillaIslands } from './src/renderer/index.ts';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  site: process.env.SITE_URL ?? 'https://oulu2026-visitor-flow.pages.dev',
  trailingSlash: 'ignore',
  integrations: [vanillaIslands()],
  build: {
    inlineStylesheets: 'auto',
  },
  vite: {
    plugins: [tailwind()],
    build: {
      // Yksi jaettu kaaviopaketti kaikille saarekkeille sen sijaan etta Observable Plot
      // toistuisi jokaisessa sirpaleessa.
      assetsInlineLimit: 1024,
    },
  },
});
