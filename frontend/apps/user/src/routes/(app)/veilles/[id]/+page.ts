import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, parent }) => {
	const { watches } = await parent();
	const watch =
		watches.find((candidate) => candidate.id === params.id) ??
		(await fromApi(() => api.watches.get(params.id)));
	return { watch };
};
