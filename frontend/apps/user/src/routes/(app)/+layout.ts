import { redirect } from '@sveltejs/kit';
import { api, session } from '@yimba/api';
import { fromApi, loginUrl } from '#lib/load.js';
import type { LayoutLoad } from './$types';

// Every page under (app) needs an account: its watches, and the number of alerts for the bell.
export const load: LayoutLoad = async ({ url, depends, untrack }) => {
	const here = untrack(() => url.pathname + url.search);
	const user = await session.restore();
	if (!user) redirect(307, loginUrl(here));

	depends('yimba:watches', 'yimba:alerts');
	return fromApi(async () => {
		const { items: watches } = await api.watches.list({ size: 100 });
		const alerts = await Promise.all(watches.map((watch) => api.watches.alerts(watch.id, { size: 100 })));
		const openAlertCount = alerts
			.flatMap((page) => page.items)
			.filter((alert) => alert.status === 'open').length;
		return { user, watches, openAlertCount };
	}, here);
};
