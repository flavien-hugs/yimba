import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

// The plugin compiles the runes of session.svelte.ts.
export default defineConfig({
	plugins: [svelte()],
	test: { environment: 'node', include: ['src/**/*.test.ts'] }
});
