import type { Watch } from '@yimba/api';

const REMEMBERED = 'yimba.veille';
const DAY = 86_400_000;

/** A URL, or the read-only one of $app/state. */
type Address = { readonly searchParams: { get(name: string): string | null } };

/** The watch the pages show: ?veille= in the address, else the last one shown, else the first. */
export function currentWatch(watches: Watch[], url: Address): Watch | null {
	const wanted = url.searchParams.get('veille') ?? remembered();
	return watches.find((watch) => watch.id === wanted) ?? watches[0] ?? null;
}

export function rememberWatch(id: string): void {
	try {
		localStorage.setItem(REMEMBERED, id);
	} catch {
		// storage blocked: the first watch is shown next time
	}
}

function remembered(): string | null {
	try {
		return localStorage.getItem(REMEMBERED);
	} catch {
		return null;
	}
}

export const PERIODS = [7, 30, 90] as const;

const PERIOD_KEY = 'yimba.periode';

/** The period shown when the address names none: the choice of the settings page, else 30 days. */
export function defaultPeriod(): number {
	try {
		const days = Number(localStorage.getItem(PERIOD_KEY));
		return (PERIODS as readonly number[]).includes(days) ? days : 30;
	} catch {
		return 30;
	}
}

export function rememberPeriod(days: number): void {
	try {
		localStorage.setItem(PERIOD_KEY, String(days));
	} catch {
		// storage blocked: 30 days next time
	}
}

/** ?periode= in days, else the default period. */
export function periodOf(url: Address): number {
	const days = Number(url.searchParams.get('periode'));
	return (PERIODS as readonly number[]).includes(days) ? days : defaultPeriod();
}

/** Start of a period of `days` UTC days, today included: the same days as the daily statistics. */
export function since(days: number, now = Date.now()): string {
	return new Date((Math.floor(now / DAY) - (days - 1)) * DAY).toISOString();
}

/** `path` with these query parameters, the empty ones left out. */
export function withQuery(path: string, params: Record<string, string | number | null | undefined>): string {
	const query = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
	}
	const search = query.toString();
	return search ? `${path}?${search}` : path;
}
