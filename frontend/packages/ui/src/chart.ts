import type { Counts } from '@yimba/api';

export interface Day {
	/** UTC day, YYYY-MM-DD: the keys of /stats?group_by=day. */
	day: string;
	negative: number;
	neutral: number;
	positive: number;
}

const DAY = 86_400_000;

/** The last `days` UTC days, today included, oldest first. */
export function lastDays(days: number, now = Date.now()): string[] {
	const today = Math.floor(now / DAY) * DAY;
	return Array.from({ length: days }, (_, index) =>
		new Date(today - (days - 1 - index) * DAY).toISOString().slice(0, 10)
	);
}

/** One entry per day of the period, zero for the days without any conversation. */
export function dailySeries(
	buckets: { key: string; counts: Counts }[],
	days: number,
	now = Date.now()
): Day[] {
	const byDay = new Map(buckets.map((bucket) => [bucket.key, bucket.counts]));
	return lastDays(days, now).map((day) => {
		const counts = byDay.get(day);
		return {
			day,
			negative: counts?.negative ?? 0,
			neutral: counts?.neutral ?? 0,
			positive: counts?.positive ?? 0
		};
	});
}

/** A round top for the axis and its graduations: 37 -> 40 (0, 10, 20, 30, 40). */
export function niceScale(max: number, steps = 4): { max: number; ticks: number[] } {
	const rough = Math.max(max, 1) / steps;
	const magnitude = 10 ** Math.floor(Math.log10(rough));
	const step = Math.max(
		1,
		[1, 2, 5, 10].map((factor) => factor * magnitude).find((value) => value >= rough)!
	);
	return { max: step * steps, ticks: Array.from({ length: steps + 1 }, (_, index) => index * step) };
}

export interface Box {
	left: number;
	top: number;
	width: number;
	height: number;
}

/** SVG paths of the stacked areas: negative at the bottom, so that its rise shows at a glance. */
export function stackedAreas(
	series: Day[],
	box: Box,
	max: number
): Record<'negative' | 'neutral' | 'positive', string> {
	const last = Math.max(series.length - 1, 1);
	const x = (index: number) => (box.left + (index * box.width) / last).toFixed(1);
	const y = (value: number) => (box.top + box.height - (value / max) * box.height).toFixed(1);
	const band = (lower: number[], upper: number[]) => {
		const top = upper.map((value, index) => `${x(index)} ${y(value)}`);
		const bottom = lower.map((value, index) => `${x(index)} ${y(value)}`).reverse();
		return `M${top.join(' L')} L${bottom.join(' L')} Z`;
	};
	const zero = series.map(() => 0);
	const negative = series.map((day) => day.negative);
	const neutral = series.map((day) => day.negative + day.neutral);
	const all = series.map((day) => day.negative + day.neutral + day.positive);
	return { negative: band(zero, negative), neutral: band(negative, neutral), positive: band(neutral, all) };
}
