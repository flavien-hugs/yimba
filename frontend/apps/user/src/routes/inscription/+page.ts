import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { session } from '@yimba/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	if (await session.restore().catch(() => null)) redirect(307, resolve('/(app)'));
};
