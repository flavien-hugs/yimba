import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { session } from '@yimba/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url }) => {
	// Where to go after login: a path of this app only, never another site.
	const asked = url.searchParams.get('suite') ?? '';
	const next =
		asked.startsWith('/') && !asked.startsWith('//') && !asked.startsWith(resolve('/connexion'))
			? asked
			: resolve('/(app)');
	if (await session.restore().catch(() => null)) redirect(307, next);
	return { next };
};
