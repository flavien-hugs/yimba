import type { Api } from './client.js';
import { ApiError } from './errors.js';
import type { User } from './types.js';

/** The signed-in account, as reactive state the pages read. */
export function createSession(api: Api) {
	let user = $state<User | null>(null);
	let restoring: Promise<User | null> | null = null;

	api.onExpired(() => {
		user = null;
		restoring = null;
	});

	async function load(): Promise<User | null> {
		if (!api.hasSession()) return null;
		try {
			return await api.me();
		} catch (error) {
			if (error instanceof ApiError && error.status === 401) return null;
			restoring = null; // the API is unreachable: try again on the next navigation
			throw error;
		}
	}

	return {
		get user(): User | null {
			return user;
		},
		/** The account of the stored session, read once per page load; null when there is none. */
		restore(): Promise<User | null> {
			if (user) return Promise.resolve(user);
			restoring ??= load().then((found) => (user = found));
			return restoring;
		},
		async login(email: string, password: string, remember: boolean): Promise<User> {
			await api.login(email, password, remember);
			const found = await api.me();
			user = found;
			return found;
		},
		async logout(): Promise<void> {
			await api.logout();
			user = null;
			restoring = null;
		},
		/** The API ends every session when the password changes: this one logs in again with the new password. */
		async changePassword(current: string, next: string): Promise<void> {
			const email = user?.email;
			if (!email) throw new ApiError(401, 'identity/missing-token', 'Not signed in');
			await api.changePassword(current, next);
			await api.login(email, next);
			user = await api.me();
		}
	};
}

export type Session = ReturnType<typeof createSession>;
