import type { Source } from '@yimba/api';
import { SOURCES } from '@yimba/ui';

/** The link of a conversation comes from a third party (a feed, a social network): only web addresses are used. */
export function webAddress(url: string | null | undefined): string | null {
	return /^https?:\/\//i.test(url ?? '') ? (url as string) : null;
}

/** Where a conversation was found: the publication or the site for the press, "Facebook · <page>" for a page... */
export function originOf(mention: { source: Source; venue?: string | null }): string {
	const platform = SOURCES[mention.source];
	if (!mention.venue) return platform;
	return mention.source === 'news' || mention.source === 'gdelt'
		? mention.venue
		: `${platform} · ${mention.venue}`;
}
