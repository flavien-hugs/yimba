import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import type { PageLoad } from './$types';

// The alerts of the watches, the most recent first.
export const load: PageLoad = async ({ parent, url, depends }) => {
	depends('yimba:alerts');
	const { watches } = await parent();
	// The header's watch button filters them (?veille=); all the watches otherwise.
	const filter = url.searchParams.get('veille');
	const shown = watches.filter((watch) => !filter || watch.id === filter);
	const pages = await fromApi(() =>
		Promise.all(shown.map((watch) => api.watches.alerts(watch.id, { size: 50 })))
	);
	const alerts = pages
		.flatMap((page) => page.items)
		.sort((a, b) => b.triggered_at.localeCompare(a.triggered_at));
	return {
		alerts,
		filter,
		handled: url.searchParams.get('etat') === 'traitees',
		watchNames: Object.fromEntries(watches.map((watch) => [watch.id, watch.name]))
	};
};
