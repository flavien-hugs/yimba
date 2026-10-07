import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import type { PageLoad } from './$types';

const PAGE_SIZE = 10;

// The alerts of the watches (?veille= for one), a state (?etat=traitees|toutes), an order (?ordre=asc), a page (?page=).
export const load: PageLoad = async ({ parent, url, depends }) => {
	depends('yimba:alerts');
	const { watches } = await parent();
	const filter = url.searchParams.get('veille');
	const state =
		(['traitees', 'toutes'] as const).find((value) => value === url.searchParams.get('etat')) ?? 'ouvertes';
	const ascending = url.searchParams.get('ordre') === 'asc';
	const requested = Math.max(1, Number(url.searchParams.get('page')) || 1);

	const shown = watches.filter((watch) => !filter || watch.id === filter);
	const pages = await fromApi(
		() => Promise.all(shown.map((watch) => api.watches.alerts(watch.id, { size: 100 }))),
		url.pathname + url.search
	);
	const everything = pages.flatMap((page) => page.items);
	const open = everything.filter((alert) => alert.status === 'open');
	const handled = everything.filter((alert) => alert.status !== 'open');
	const wanted = state === 'ouvertes' ? open : state === 'traitees' ? handled : everything;
	const sorted = [...wanted].sort((a, b) =>
		ascending ? a.triggered_at.localeCompare(b.triggered_at) : b.triggered_at.localeCompare(a.triggered_at)
	);
	const total = sorted.length;
	const count = Math.max(1, Math.ceil(total / PAGE_SIZE));
	const current = Math.min(requested, count);
	const latest =
		everything
			.map((alert) => alert.triggered_at)
			.sort()
			.at(-1) ?? null;

	return {
		alerts: sorted.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE),
		open: open.map((alert) => ({ id: alert.id, watch_id: alert.watch_id })),
		pageNumber: current,
		pages: count,
		total,
		pageSize: PAGE_SIZE,
		counts: { open: open.length, handled: handled.length, all: everything.length },
		latest,
		state,
		ascending,
		filter,
		watchNames: Object.fromEntries(watches.map((watch) => [watch.id, watch.name]))
	};
};
