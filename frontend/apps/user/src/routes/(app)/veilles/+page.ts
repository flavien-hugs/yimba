import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import { since } from '#lib/watch.js';
import type { PageLoad } from './$types';

const DAYS = 30;
// Cards take more room than rows: eight cards or ten rows per page.
const PAGE_SIZES = { cartes: 8, liste: 10 } as const;
const STATES = { actives: true, pause: false } as const;

// A page of watches (?page, ?etat=actives|pause, ?q), each with its conversations of the last 30 days and its alerts.
export const load: PageLoad = async ({ url, depends }) => {
	depends('yimba:watches', 'yimba:alerts');
	const state = url.searchParams.get('etat') as keyof typeof STATES | null;
	const filter = state && state in STATES ? state : null;
	const search = url.searchParams.get('q')?.trim() ?? '';
	const requested = Math.max(1, Number(url.searchParams.get('page')) || 1);
	const day = (name: string) => {
		const value = url.searchParams.get(name) ?? '';
		return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null;
	};
	const created = { from: day('du'), to: day('au') };
	const sort = url.searchParams.get('tri') === 'nom' ? 'name' : 'created';
	const order = url.searchParams.get('ordre') === 'asc' ? 'asc' : 'desc';
	const view = url.searchParams.get('vue') === 'cartes' ? 'cartes' : 'liste';
	const size = PAGE_SIZES[view];
	const start = since(DAYS);

	return fromApi(async () => {
		const [page, all, active] = await Promise.all([
			api.watches.list({
				page: requested,
				size,
				search: search || undefined,
				active: filter ? STATES[filter] : undefined,
				created_from: created.from ?? undefined,
				created_to: created.to ?? undefined,
				sort,
				order
			}),
			api.watches.list({ size: 1 }),
			api.watches.list({ size: 1, active: true })
		]);
		const summaries = await Promise.all(
			page.items.map(async (watch) => {
				const [stats, alerts] = await Promise.all([
					api.watches.stats(watch.id, { group_by: 'source', start }),
					api.watches.alerts(watch.id, { size: 100 })
				]);
				return [
					watch.id,
					{ totals: stats.totals, openAlerts: alerts.items.filter((alert) => alert.status === 'open').length }
				] as const;
			})
		);
		return {
			days: DAYS,
			view,
			page,
			pages: Math.max(1, Math.ceil(page.total / size)),
			counts: { all: all.total, actives: active.total, pause: all.total - active.total },
			filter,
			created,
			sort,
			order,
			search,
			summaries: Object.fromEntries(summaries)
		};
	}, url.pathname + url.search);
};
