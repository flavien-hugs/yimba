import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import { since } from '#lib/watch.js';
import type { PageLoad } from './$types';

const DAYS = 30;

// For each watch: its conversations of the last 30 days and the alerts still to handle.
export const load: PageLoad = async ({ parent, depends }) => {
	depends('yimba:watches', 'yimba:alerts');
	const { watches } = await parent();
	const start = since(DAYS);
	const summaries = await fromApi(() =>
		Promise.all(
			watches.map(async (watch) => {
				const [stats, alerts] = await Promise.all([
					api.watches.stats(watch.id, { group_by: 'source', start }),
					api.watches.alerts(watch.id, { size: 100 })
				]);
				return [
					watch.id,
					{ totals: stats.totals, openAlerts: alerts.items.filter((alert) => alert.status === 'open').length }
				] as const;
			})
		)
	);
	return { days: DAYS, summaries: Object.fromEntries(summaries) };
};
