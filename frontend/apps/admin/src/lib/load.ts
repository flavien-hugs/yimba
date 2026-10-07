import { error, redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { ApiError, describe } from '@yimba/api';

/** The login page, coming back to `next` afterwards. */
export function loginUrl(next?: string): string {
	return next ? `${resolve('/connexion')}?suite=${encodeURIComponent(next)}` : resolve('/connexion');
}

/** Runs the API calls of a load function: an expired session goes back to login, other errors to the error page. */
export async function fromApi<T>(run: () => Promise<T>, next?: string): Promise<T> {
	try {
		return await run();
	} catch (caught) {
		if (!(caught instanceof ApiError)) throw caught;
		if (caught.status === 401) redirect(307, loginUrl(next));
		error(caught.status || 503, describe(caught), { code: caught.code });
	}
}
