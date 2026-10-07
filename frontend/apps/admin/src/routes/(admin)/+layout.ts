import { error, redirect } from '@sveltejs/kit';
import { session } from '@yimba/api';
import { loginUrl } from '#lib/load.js';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ url, untrack }) => {
	const user = await session.restore();
	if (!user) redirect(307, loginUrl(untrack(() => url.pathname + url.search)));
	if (user.role !== 'admin')
		error(403, "Ce compte n'a pas accès à l'administration.", { code: 'identity/not-admin' });
	return { user };
};
