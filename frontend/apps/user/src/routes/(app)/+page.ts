import { api } from '@yimba/api';
import { fromApi } from '#lib/load.js';
import { currentWatch, periodOf, since } from '#lib/watch.js';
import type { PageLoad } from './$types';

const DAY = 86_400_000;

export const load: PageLoad = async ({ parent, url }) => {
	const { watches } = await parent();
	const watch = currentWatch(watches, url);
	if (!watch) return { dashboard: null };

	const days = periodOf(url);
	const now = Date.now();
	const period = { start: since(days, now) };
	const stats = api.watches.stats;
	const [daily, bySource, byLanguage, lastDay, previous, voices, alerts, places, themes] = await fromApi(() =>
		Promise.all([
			stats(watch.id, { group_by: 'day', ...period }),
			stats(watch.id, { group_by: 'source', ...period }),
			stats(watch.id, { group_by: 'language', ...period }),
			stats(watch.id, { group_by: 'source', start: new Date(now - DAY).toISOString() }),
			// The same number of days just before, to say whether things change.
			stats(watch.id, { group_by: 'source', start: since(days * 2, now), end: period.start }),
			api.watches.mentions(watch.id, { size: 3 }),
			api.watches.alerts(watch.id, { size: 20 }),
			api.watches.places(watch.id, period),
			api.watches.themes(watch.id, { ...period, limit: 6 })
		])
	);
	return {
		dashboard: {
			watch,
			days,
			now,
			daily,
			bySource: bySource.buckets,
			byLanguage: byLanguage.buckets,
			lastDay: lastDay.totals,
			previous: previous.totals,
			voices: voices.items,
			places,
			themes: themes.themes,
			watchAlerts: alerts.items.filter((alert) => alert.status === 'open')
		}
	};
};
