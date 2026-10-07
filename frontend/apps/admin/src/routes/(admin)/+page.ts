import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import type { PageLoad } from './$types';

const PAGE_SIZE = 20;

export const load: PageLoad = async ({ url, depends }) => {
	depends('yimba:users');
	const search = url.searchParams.get('q')?.trim() ?? '';
	const withDeleted = url.searchParams.get('supprimes') === '1';
	const pageNumber = Math.max(1, Number(url.searchParams.get('page')) || 1);
	const users = await fromApi(
		() =>
			api.users.list({
				search: search || undefined,
				include_deleted: withDeleted,
				page: pageNumber,
				size: PAGE_SIZE
			}),
		url.pathname + url.search
	);
	return { users, search, withDeleted, pages: Math.max(1, Math.ceil(users.total / PAGE_SIZE)) };
};
