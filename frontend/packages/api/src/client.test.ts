import { describe as group, expect, it, vi } from 'vitest';
import { createApi } from './client.js';
import { ApiError, describe } from './errors.js';
import { createSession } from './session.svelte.js';
import { memoryTokenStore } from './tokens.js';

const USER = { id: 'u1', email: 'awa@example.org', full_name: 'Awa Koné', role: 'user', active: true };

/** A fake backend: rotates refresh tokens, accepts the latest access token only. */
function backend() {
	let generation = 0;
	let accessToken = '';
	let refreshToken = '';
	const calls: string[] = [];
	const pair = () => {
		generation += 1;
		accessToken = `access-${generation}`;
		refreshToken = `refresh-${generation}`;
		return { access_token: accessToken, token_type: 'bearer', expires_in: 900, refresh_token: refreshToken };
	};
	const json = (status: number, body?: unknown) =>
		new Response(body === undefined ? null : JSON.stringify(body), { status });

	const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
		const path = String(input);
		const body = init?.body ? JSON.parse(String(init.body)) : {};
		const authorization = new Headers(init?.headers).get('authorization');
		calls.push(`${init?.method} ${path}`);
		if (path === '/api/auth/login') {
			return body.password === 'correct horse'
				? json(200, pair())
				: json(401, { code: 'identity/invalid-credentials', message: 'Invalid credentials' });
		}
		if (path === '/api/auth/refresh') {
			return body.refresh_token === refreshToken
				? json(200, pair())
				: json(401, { code: 'identity/invalid-refresh-token', message: 'Invalid' });
		}
		if (path === '/api/auth/logout') return json(204);
		if (authorization !== `Bearer ${accessToken}`) {
			return json(401, { code: 'identity/invalid-token', message: 'Invalid or expired token' });
		}
		if (path === '/api/auth/me') return json(200, USER);
		if (path.startsWith('/api/watches?')) return json(200, { items: [], total: 0, page: 1, size: 20 });
		return json(404, { code: 'watch/not-found', message: 'Not found' });
	});

	return {
		fetch,
		calls,
		revokeAccess: () => (accessToken = 'revoked'),
		revokeRefresh: () => (refreshToken = 'revoked')
	};
}

function setup() {
	const server = backend();
	const store = memoryTokenStore();
	let clock = 1_000_000;
	const api = createApi({ store, fetch: server.fetch, now: () => clock, lock: (run) => run() });
	return { api, store, server, advance: (ms: number) => (clock += ms) };
}

group('createApi', () => {
	it('logs in, keeps the refresh token where asked and sends the access token', async () => {
		const { api, store, server } = setup();
		await api.login('awa@example.org', 'correct horse', true);
		expect(store.read()).toBe('refresh-1');
		expect(store.remembered).toBe(true);
		await expect(api.me()).resolves.toMatchObject({ email: 'awa@example.org' });
		expect(server.calls).toEqual(['POST /api/auth/login', 'GET /api/auth/me']);
	});

	it('refreshes the access token shortly before it expires, once for concurrent calls', async () => {
		const { api, store, server, advance } = setup();
		await api.login('awa@example.org', 'correct horse');
		advance(900_000 - 10_000);
		await Promise.all([api.me(), api.watches.list({ page: 1 })]);
		expect(server.calls.filter((call) => call.includes('/auth/refresh'))).toHaveLength(1);
		expect(store.read()).toBe('refresh-2');
	});

	it('resumes a stored session with the refresh token alone', async () => {
		const first = setup();
		await first.api.login('awa@example.org', 'correct horse');
		const later = createApi({ store: first.store, fetch: first.server.fetch, lock: (run) => run() });
		expect(later.hasSession()).toBe(true);
		await expect(later.me()).resolves.toMatchObject({ id: 'u1' });
	});

	it('refreshes and retries once when the access token is refused', async () => {
		const { api, server } = setup();
		await api.login('awa@example.org', 'correct horse');
		server.revokeAccess();
		await expect(api.me()).resolves.toMatchObject({ id: 'u1' });
		expect(server.calls.slice(-3)).toEqual([
			'GET /api/auth/me',
			'POST /api/auth/refresh',
			'GET /api/auth/me'
		]);
	});

	it('ends the session when the refresh token is refused', async () => {
		const { api, store, server } = setup();
		const expired = vi.fn();
		api.onExpired(expired);
		await api.login('awa@example.org', 'correct horse');
		server.revokeAccess();
		server.revokeRefresh();
		await expect(api.me()).rejects.toMatchObject({ status: 401 });
		expect(expired).toHaveBeenCalledOnce();
		expect(store.read()).toBeNull();
		expect(api.hasSession()).toBe(false);
	});

	it('turns error bodies into ApiError', async () => {
		const { api } = setup();
		const error = await api.login('awa@example.org', 'wrong').catch((caught: unknown) => caught);
		expect(error).toBeInstanceOf(ApiError);
		expect(error).toMatchObject({ status: 401, code: 'identity/invalid-credentials' });
	});

	it('reports an unreachable API as a network error', async () => {
		const api = createApi({
			store: memoryTokenStore(),
			fetch: () => Promise.reject(new TypeError('Failed to fetch'))
		});
		await expect(api.login('a@b.org', 'x')).rejects.toMatchObject({ status: 0, code: 'network' });
	});

	it('ends the session a new login replaces', async () => {
		const { api, server } = setup();
		await api.login('awa@example.org', 'correct horse');
		await api.login('awa@example.org', 'correct horse');
		await vi.waitFor(() => expect(server.calls.at(-1)).toBe('POST /api/auth/logout'));
	});

	it('logs out: the refresh token is sent to the API, then forgotten', async () => {
		const { api, store, server } = setup();
		await api.login('awa@example.org', 'correct horse');
		await api.logout();
		expect(server.calls.at(-1)).toBe('POST /api/auth/logout');
		expect(store.read()).toBeNull();
	});
});

group('createSession', () => {
	it('restores, logs in and logs out', async () => {
		const { api } = setup();
		const session = createSession(api);
		await expect(session.restore()).resolves.toBeNull();
		await session.login('awa@example.org', 'correct horse', false);
		expect(session.user?.full_name).toBe('Awa Koné');
		await session.logout();
		expect(session.user).toBeNull();
	});
});

group('describe', () => {
	it('speaks French, with the lengths of the password policy', () => {
		const weak = new ApiError(
			422,
			'identity/weak-password',
			'the password must have between 12 and 128 characters'
		);
		expect(describe(weak)).toBe('Le mot de passe doit compter entre 12 et 128 caractères.');
		expect(describe(new ApiError(0, 'network', ''))).toMatch(/Impossible de joindre Yimba/);
		expect(describe(new ApiError(500, 'http/500', ''))).toMatch(/problème/);
		expect(describe(new ApiError(502, 'http/502', 'Bad Gateway'))).toMatch(/Impossible de joindre Yimba/);
		expect(describe(new ApiError(502, 'collection/gdelt-unreachable', ''))).toMatch(/service extérieur/);
		expect(describe(new Error('boom'))).toMatch(/inattendue/);
	});
});
