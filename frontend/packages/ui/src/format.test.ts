import { describe, expect, it } from 'vitest';
import { dailySeries, lastDays, niceScale, stackedAreas } from './chart.js';
import { firstName, formatAgo, formatMoment, formatNumber, formatShare, initials, plural } from './format.js';

const NOW = new Date(2026, 9, 6, 15, 30).getTime(); // Tuesday 6 October 2026, 15:30 local time
/** Intl puts no-break spaces (U+00A0, U+202F) where French typography wants them: compare with plain spaces. */
const plain = (text: string) => text.replace(/[\u00a0\u202f]/g, ' ');

describe('format', () => {
	it('writes numbers and shares the French way', () => {
		expect(plain(formatNumber(5840))).toBe('5 840');
		expect(plain(formatShare(0.342))).toBe('34 %');
		expect(plural(1, 'conversation')).toBe('1 conversation');
		expect(plain(plural(1012, 'conversation'))).toBe('1 012 conversations');
		expect(plural(2, 'conversation')).toBe('2 conversations');
	});

	it('says how long ago', () => {
		expect(plain(formatAgo(new Date(NOW - 20_000), NOW))).toBe("à l'instant");
		expect(plain(formatAgo(new Date(NOW - 12 * 60_000), NOW))).toBe('il y a 12 min');
		expect(plain(formatAgo(new Date(NOW - 3 * 3_600_000), NOW))).toBe('il y a 3 h');
		expect(plain(formatAgo(new Date(NOW - 26 * 3_600_000), NOW))).toBe('hier');
	});

	it('dates a moment relative to today', () => {
		expect(formatMoment(new Date(2026, 9, 6, 11, 2), NOW)).toBe("aujourd'hui à 11 h 02");
		expect(formatMoment(new Date(2026, 9, 5, 18, 40), NOW)).toBe('hier à 18 h 40');
		expect(formatMoment(new Date(2026, 9, 3, 9, 15), NOW)).toBe('le 3 octobre à 9 h 15');
	});

	it('finds initials and first names', () => {
		expect(initials('Awa Koné', 'awa@example.org')).toBe('AK');
		expect(initials(null, 'awa@example.org')).toBe('AW');
		expect(firstName('Awa Koné', 'awa@example.org')).toBe('Awa');
		expect(firstName('', 'kouame@example.org')).toBe('kouame');
	});
});

describe('chart', () => {
	it('lists the days of the period, oldest first', () => {
		const days = lastDays(3, Date.UTC(2026, 9, 6, 12));
		expect(days).toEqual(['2026-10-04', '2026-10-05', '2026-10-06']);
	});

	it('fills the days without conversations with zeros', () => {
		const counts = { total: 3, positive: 1, neutral: 0, negative: 2, negative_share: 0.67 };
		const series = dailySeries([{ key: '2026-10-05', counts }], 3, Date.UTC(2026, 9, 6, 12));
		expect(series.map((day) => day.negative)).toEqual([0, 2, 0]);
	});

	it('rounds the axis up', () => {
		expect(niceScale(37)).toEqual({ max: 40, ticks: [0, 10, 20, 30, 40] });
		expect(niceScale(0).max).toBe(4);
		expect(niceScale(380).max).toBe(400);
	});

	it('draws closed areas, the negative one on the baseline', () => {
		const series = [
			{ day: 'a', negative: 10, neutral: 10, positive: 20 },
			{ day: 'b', negative: 20, neutral: 0, positive: 20 }
		];
		const areas = stackedAreas(series, { left: 0, top: 0, width: 100, height: 40 }, 40);
		expect(areas.negative).toBe('M0.0 30.0 L100.0 20.0 L100.0 40.0 L0.0 40.0 Z');
		expect(areas.positive.startsWith('M0.0 0.0 L100.0 0.0')).toBe(true);
	});
});
