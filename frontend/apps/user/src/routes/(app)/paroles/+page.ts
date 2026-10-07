import { api, type Emotion, type Sentiment, type Source } from '@yimba/api';
import { EMOTIONS, SENTIMENTS, SOURCES } from '@yimba/ui';
import { fromApi } from '#lib/load.js';
import { currentWatch, periodOf, since } from '#lib/watch.js';
import type { PageLoad } from './$types';

// Ten at a time, as in the design: "Voir 10 conversations de plus".
const PAGE_SIZE = 10;

export const load: PageLoad = async ({ parent, url }) => {
	const { watches } = await parent();
	const watch = currentWatch(watches, url);
	if (!watch) return { listing: null };

	const params = url.searchParams;
	const pick = <T extends string>(name: string, allowed: Record<T, unknown>): T | undefined => {
		const value = params.get(name);
		return value && value in allowed ? (value as T) : undefined;
	};
	const filters = {
		sentiment: pick<Sentiment>('ressenti', SENTIMENTS),
		source: pick<Source>('source', SOURCES),
		emotion: pick<Emotion>('emotion', EMOTIONS),
		language: params.get('langue') || undefined,
		q: params.get('q')?.trim() || undefined
	};
	// An alert links to its own window (debut, fin); otherwise the last `periode` days.
	const days = periodOf(url);
	const start = isDate(params.get('debut')) ? params.get('debut')! : since(days);
	const end = isDate(params.get('fin')) ? params.get('fin')! : undefined;
	const window = { start, end };

	const [mentions, stats] = await fromApi(() =>
		Promise.all([
			api.watches.mentions(watch.id, { ...filters, ...window, page: 1, size: PAGE_SIZE }),
			api.watches.stats(watch.id, {
				group_by: 'source',
				source: filters.source,
				language: filters.language,
				...window
			})
		])
	);
	return {
		listing: {
			watch,
			filters,
			days,
			window,
			explicitWindow: end !== undefined,
			mentions,
			totals: stats.totals,
			pageSize: PAGE_SIZE
		}
	};
};

function isDate(value: string | null): boolean {
	return value !== null && !Number.isNaN(Date.parse(value));
}
