// Numbers, shares and dates the French way: "5 840", "34 %", "il y a 12 min", "aujourd'hui à 11 h 02".

const numbers = new Intl.NumberFormat('fr-FR');
const shares = new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 0 });
const relative = new Intl.RelativeTimeFormat('fr', { numeric: 'auto', style: 'short' });
const dayMonth = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' });
const dayMonthYear = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
const weekday = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export function formatNumber(value: number): string {
	return numbers.format(value);
}

/** 0.342 -> "34 %". */
export function formatShare(share: number): string {
	return shares.format(share);
}

/** 0.342 -> 34. */
export function percent(share: number): number {
	return Math.round(share * 100);
}

/** "il y a 12 min", "il y a 3 h", "hier", "il y a 5 j". */
export function formatAgo(date: string | Date, now = Date.now()): string {
	const elapsed = now - new Date(date).getTime();
	if (elapsed < MINUTE) return "à l'instant";
	if (elapsed < HOUR) return relative.format(-Math.floor(elapsed / MINUTE), 'minute');
	if (elapsed < DAY) return relative.format(-Math.floor(elapsed / HOUR), 'hour');
	if (elapsed < 30 * DAY) return relative.format(-Math.floor(elapsed / DAY), 'day');
	return `le ${formatDate(date, now)}`;
}

/** "11 h 02". */
export function formatClock(date: string | Date): string {
	const moment = new Date(date);
	return `${moment.getHours()} h ${String(moment.getMinutes()).padStart(2, '0')}`;
}

/** "aujourd'hui à 11 h 02", "hier à 18 h 40", "le 3 octobre à 9 h 15". */
export function formatMoment(date: string | Date, now = Date.now()): string {
	const days = daysBetween(new Date(date), new Date(now));
	const clock = formatClock(date);
	if (days === 0) return `aujourd'hui à ${clock}`;
	if (days === 1) return `hier à ${clock}`;
	return `le ${formatDate(date, now)} à ${clock}`;
}

/** "6 octobre", with the year when it is not the current one. */
export function formatDate(date: string | Date, now = Date.now()): string {
	const moment = new Date(date);
	const format = moment.getFullYear() === new Date(now).getFullYear() ? dayMonth : dayMonthYear;
	return format.format(moment);
}

/** "Mardi 6 octobre". */
export function formatToday(now = Date.now()): string {
	const text = weekday.format(new Date(now));
	return text.charAt(0).toUpperCase() + text.slice(1);
}

const compact = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 });

/** 842 -> "842", 12 400 -> "12,4 k", 3 100 000 -> "3,1 M": for the small figures of a card. */
export function formatCompact(value: number): string {
	return value < 10_000 ? formatNumber(value) : compact.format(value);
}

const LINK = /https?:\/\/\S+|www\.\S+/g;
const SENTENCE_END = /(?<=[.!?…])\s+/;

/**
 * A short version of a text, for a card: its first sentences up to `max` characters, or its first words and "…".
 * Links are left out (a link says nothing in a summary).
 */
export function summarize(text: string, max = 200): string {
	const clean = text.replace(LINK, ' ').split(/\s+/).filter(Boolean).join(' ');
	if (clean.length <= max) return clean;
	let summary = '';
	for (const sentence of clean.split(SENTENCE_END)) {
		const next = summary ? `${summary} ${sentence}` : sentence;
		if (next.length > max) break;
		summary = next;
	}
	if (summary) return summary;
	const cut = clean.slice(0, max - 1);
	return `${cut.slice(0, cut.lastIndexOf(' ') > max / 2 ? cut.lastIndexOf(' ') : cut.length).replace(/[\s,;:.-]+$/, '')}…`;
}

/** "1 conversation", "2 conversations". */
export function plural(count: number, one: string, many = `${one}s`): string {
	return `${formatNumber(count)} ${count > 1 ? many : one}`;
}

/** "AK" for Awa Koné, "AW" for awa@example.org. */
export function initials(name: string | null | undefined, email: string): string {
	const words = (name ?? '').trim().split(/\s+/).filter(Boolean);
	if (words.length >= 2) return (words[0][0] + words[words.length - 1][0]).toUpperCase();
	return (words[0] ?? email).slice(0, 2).toUpperCase();
}

export function firstName(name: string | null | undefined, email: string): string {
	return (name ?? '').trim().split(/\s+/)[0] || email.split('@')[0];
}

function daysBetween(earlier: Date, later: Date): number {
	const start = new Date(earlier.getFullYear(), earlier.getMonth(), earlier.getDate());
	const end = new Date(later.getFullYear(), later.getMonth(), later.getDate());
	return Math.round((end.getTime() - start.getTime()) / DAY);
}
