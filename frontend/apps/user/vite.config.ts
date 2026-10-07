import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, type ProxyOptions } from 'vite';

// In development Vite forwards /api to the backend, as nginx does in the image: same origin, no CORS.
const api: Record<string, ProxyOptions> = {
	'/api': {
		target: process.env.YIMBA_API_URL ?? 'http://localhost:8800',
		changeOrigin: true,
		rewrite: (path) => path.replace(/^\/api/, '')
	}
};

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
			},
			// A single-page app: every route falls back to 200.html, the data comes from the API in the browser.
			adapter: adapter({ fallback: '200.html', precompress: true }),
			paths: { base: '' },
			csp: {
				mode: 'hash',
				directives: {
					'default-src': ['self'],
					'script-src': ['self'],
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'font-src': ['self'],
					'connect-src': ['self'],
					'object-src': ['none'],
					'base-uri': ['self'],
					'form-action': ['self']
				}
			}
		})
	],
	server: { port: 5173, strictPort: true, proxy: api },
	preview: { port: 5173, strictPort: true, proxy: api }
});
