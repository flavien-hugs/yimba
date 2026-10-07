import { ApiError, errorFrom } from './errors.js';
import type { TokenStore } from './tokens.js';
import type {
	Alert,
	AlertQuery,
	MentionQuery,
	Mention,
	Page,
	Places,
	PlacesQuery,
	Registration,
	Stats,
	StatsQuery,
	Themes,
	ThemesQuery,
	TokenPair,
	User,
	UserQuery,
	UserUpdate,
	Watch,
	WatchCreate,
	WatchQuery,
	WatchUpdate
} from './types.js';

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE';
type QueryValue = string | number | boolean | null | undefined;

interface Call {
	query?: Record<string, QueryValue>;
	body?: unknown;
	/** false for the routes that take no access token (login, refresh...). */
	auth?: boolean;
}

export interface ApiOptions {
	store: TokenStore;
	/** The API, through the same origin: nginx (image) and Vite (development) proxy /api to the backend. */
	baseUrl?: string;
	fetch?: typeof fetch;
	now?: () => number;
	/** Serializes the refreshes of every tab: a refresh token works once, two tabs must not spend the same one. */
	lock?: <T>(run: () => Promise<T>) => Promise<T>;
}

/** Refresh the access token this long before it expires. */
const EARLY_REFRESH_MS = 30_000;

export function webLock<T>(run: () => Promise<T>): Promise<T> {
	const locks = globalThis.navigator?.locks;
	return locks ? locks.request('yimba-refresh', run) : run();
}

export function createApi({
	store,
	baseUrl = '/api',
	fetch: fetcher = (input, init) => globalThis.fetch(input, init),
	now = Date.now,
	lock = webLock
}: ApiOptions) {
	let access: { token: string; expiresAt: number } | null = null;
	let refreshing: Promise<boolean> | null = null;
	const expiredListeners = new Set<() => void>();

	store.onCleared(() => expire());

	function url(path: string, query: Call['query'] = {}): string {
		const params = new URLSearchParams();
		for (const [key, value] of Object.entries(query)) {
			if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
		}
		const search = params.toString();
		return `${baseUrl}${path}${search ? `?${search}` : ''}`;
	}

	async function send(method: Method, path: string, { query, body, auth = true }: Call): Promise<Response> {
		const headers: Record<string, string> = { accept: 'application/json' };
		if (body !== undefined) headers['content-type'] = 'application/json';
		if (auth && access) headers.authorization = `Bearer ${access.token}`;
		try {
			return await fetcher(url(path, query), {
				method,
				headers,
				body: body === undefined ? undefined : JSON.stringify(body)
			});
		} catch {
			throw new ApiError(0, 'network', 'The API could not be reached');
		}
	}

	function keep(pair: TokenPair, remember?: boolean): void {
		access = { token: pair.access_token, expiresAt: now() + pair.expires_in * 1000 };
		store.write(pair.refresh_token, remember);
	}

	function forget(): void {
		access = null;
		store.clear();
	}

	/** The session is over (refused, revoked, or ended in another tab): forget it and tell the app. */
	function expire(): void {
		const hadSession = access !== null || store.read() !== null;
		forget();
		if (hadSession) expiredListeners.forEach((listener) => listener());
	}

	/** Exchanges the refresh token for a new pair; false when there is none or it is refused. */
	function refresh(): Promise<boolean> {
		refreshing ??= lock(async () => {
			// Read inside the lock: another tab may have just rotated the token.
			const token = store.read();
			if (!token) return false;
			const response = await send('POST', '/auth/refresh', { body: { refresh_token: token }, auth: false });
			if (response.ok) {
				keep((await response.json()) as TokenPair);
				return true;
			}
			if (response.status === 401) return false;
			throw await errorFrom(response);
		}).finally(() => {
			refreshing = null;
		});
		return refreshing;
	}

	async function ensureAccess(): Promise<void> {
		if (access && access.expiresAt - EARLY_REFRESH_MS > now()) return;
		if (await refresh()) return;
		expire();
		throw new ApiError(401, 'identity/session-expired', 'The session has expired');
	}

	async function request<T>(method: Method, path: string, call: Call = {}): Promise<T> {
		const auth = call.auth ?? true;
		if (auth) await ensureAccess();
		let response = await send(method, path, call);
		if (auth && response.status === 401) {
			// Access token refused although not expired (password changed, account disabled): refresh once, retry once.
			if (await refresh()) response = await send(method, path, call);
			if (response.status === 401) {
				const error = await errorFrom(response);
				expire();
				throw error;
			}
		}
		if (!response.ok) throw await errorFrom(response);
		return (response.status === 204 ? undefined : await response.json()) as T;
	}

	/** Ends the session of a refresh token on the API; best effort, the token is already forgotten here. */
	async function revoke(token: string): Promise<void> {
		await send('POST', '/auth/logout', { body: { refresh_token: token }, auth: false })
			.then((response) => response.body?.cancel())
			.catch(() => {});
	}

	const watch = (id: string) => `/watches/${encodeURIComponent(id)}`;

	return {
		/** A session to resume: an access token, or a refresh token from an earlier visit. */
		hasSession: (): boolean => access !== null || store.read() !== null,
		onExpired(listener: () => void): () => void {
			expiredListeners.add(listener);
			return () => expiredListeners.delete(listener);
		},

		async login(email: string, password: string, remember?: boolean): Promise<void> {
			const pair = await request<TokenPair>('POST', '/auth/login', {
				body: { email, password },
				auth: false
			});
			// One session per browser: the one this login replaces (another account, another tab) ends.
			const previous = store.read();
			keep(pair, remember);
			if (previous) void revoke(previous);
		},
		register: (registration: Registration) =>
			request<User>('POST', '/auth/register', { body: registration, auth: false }),
		async logout(): Promise<void> {
			const token = store.read();
			forget();
			if (token) await revoke(token);
		},
		me: () => request<User>('GET', '/auth/me'),
		/** Ends every session of the account, this one included: log in again with the new password. */
		changePassword: (current: string, next: string) =>
			request<void>('POST', '/auth/password', { body: { current_password: current, new_password: next } }),

		watches: {
			list: (query: WatchQuery = {}) => request<Page<Watch>>('GET', '/watches', { query }),
			get: (id: string) => request<Watch>('GET', watch(id)),
			create: (body: WatchCreate) => request<Watch>('POST', '/watches', { body }),
			update: (id: string, body: WatchUpdate) => request<Watch>('PATCH', watch(id), { body }),
			remove: (id: string) => request<void>('DELETE', watch(id)),
			mentions: (id: string, query: MentionQuery = {}) =>
				request<Page<Mention>>('GET', `${watch(id)}/mentions`, { query }),
			stats: (id: string, query: StatsQuery = {}) => request<Stats>('GET', `${watch(id)}/stats`, { query }),
			places: (id: string, query: PlacesQuery = {}) =>
				request<Places>('GET', `${watch(id)}/places`, { query }),
			themes: (id: string, query: ThemesQuery = {}) =>
				request<Themes>('GET', `${watch(id)}/themes`, { query }),
			alerts: (id: string, query: AlertQuery = {}) =>
				request<Page<Alert>>('GET', `${watch(id)}/alerts`, { query }),
			acknowledge: (id: string, alertId: string) =>
				request<Alert>('POST', `${watch(id)}/alerts/${encodeURIComponent(alertId)}/acknowledge`)
		},

		users: {
			list: (query: UserQuery = {}) => request<Page<User>>('GET', '/users', { query }),
			update: (id: string, body: UserUpdate) =>
				request<User>('PATCH', `/users/${encodeURIComponent(id)}`, { body }),
			remove: (id: string) => request<void>('DELETE', `/users/${encodeURIComponent(id)}`)
		}
	};
}

export type Api = ReturnType<typeof createApi>;
