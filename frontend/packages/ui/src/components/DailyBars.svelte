<!-- The last days as stacked bars (the phone version of the opinion chart): negative, neutral, positive. -->
<script lang="ts">
	import type { Day } from '../chart.js';

	interface Props {
		series: Day[];
		/** Read by screen readers instead of the drawing. */
		description: string;
	}

	let { series, description }: Props = $props();

	const weekday = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', timeZone: 'UTC' });
	const BASE = 128;
	const TOP = 4;
	const max = $derived(Math.max(1, ...series.map((day) => day.negative + day.neutral + day.positive)));
	const height = (count: number) => (count / max) * (BASE - TOP);
	const bars = $derived(
		series.map((day, index) => {
			const negative = height(day.negative);
			const neutral = height(day.neutral);
			const positive = height(day.positive);
			const label =
				index === series.length - 1
					? 'auj.'
					: weekday.format(new Date(`${day.day}T00:00:00Z`)).replace(/\.$/, '');
			return { day: day.day, negative, neutral, positive, label };
		})
	);
	const step = $derived(series.length > 1 ? (330 - 8 - 34 - 6) / (series.length - 1) : 0);
</script>

<svg viewBox="0 0 330 150" class="h-auto w-full" role="img" aria-label={description}>
	<line x1="0" x2="330" y1={BASE} y2={BASE} class="stroke-rule" />
	{#each bars as bar, index (bar.day)}
		{@const x = 8 + index * step}
		<rect {x} y={BASE - bar.negative} width="34" height={bar.negative} rx="3" class="fill-clay" />
		<rect {x} y={BASE - bar.negative - bar.neutral} width="34" height={bar.neutral} class="fill-sand" />
		<rect
			{x}
			y={BASE - bar.negative - bar.neutral - bar.positive}
			width="34"
			height={bar.positive}
			rx="3"
			class="fill-leaf"
		/>
		<text x={x + 17} y="145" text-anchor="middle" class="fill-muted text-xs">{bar.label}</text>
	{/each}
</svg>
