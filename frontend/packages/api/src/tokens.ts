/**
 * Where the refresh token lives between page loads. The access token never leaves memory.
 *
 * "Rester connecté·e" keeps it in localStorage (shared by the tabs, survives closing the browser); otherwise it goes
 * to sessionStorage and ends with the tab. A rotation writes the new token where the previous one was.
 */
export interface TokenStore {
	read(): string | null;
	/** `remember` undefined: keep the token where it already is. */
	write(token: string, remember?: boolean): void;
	clear(): void;
	/** Calls `listener` when another tab ends the session. */
	onCleared(listener: () => void): void;
}

const KEY = 'yimba.session';

export function browserTokenStore(key = KEY): TokenStore {
	const shared = storage('localStorage');
	const tab = storage('sessionStorage');
	const get = (place: Storage | null) => attempt(() => place?.getItem(key) ?? null, null);
	const put = (place: Storage | null, token: string | null) =>
		attempt(() => (token === null ? place?.removeItem(key) : place?.setItem(key, token)), undefined);

	return {
		read: () => get(tab) ?? get(shared),
		write(token, remember) {
			const keep = remember ?? get(shared) !== null;
			put(keep ? shared : tab, token);
			put(keep ? tab : shared, null);
		},
		clear() {
			put(shared, null);
			put(tab, null);
		},
		onCleared(listener) {
			globalThis.addEventListener?.('storage', (event: StorageEvent) => {
				if ((event.key === key || event.key === null) && event.newValue === null) listener();
			});
		}
	};
}

/** For tests, and wherever no Web Storage exists. */
export function memoryTokenStore(): TokenStore & { remembered: boolean } {
	let token: string | null = null;
	return {
		remembered: false,
		read: () => token,
		write(value, remember) {
			token = value;
			if (remember !== undefined) this.remembered = remember;
		},
		clear() {
			token = null;
		},
		onCleared() {}
	};
}

function storage(name: 'localStorage' | 'sessionStorage'): Storage | null {
	// Reading the property itself throws when site data is blocked.
	return (
		attempt(() => (globalThis as Record<string, unknown>)[name] as Storage | undefined, undefined) ?? null
	);
}

function attempt<T>(run: () => T, fallback: T): T {
	try {
		return run();
	} catch {
		return fallback;
	}
}
