<!-- Conversations per day, stacked: negative at the bottom, then neutral, then positive. -->
<script lang="ts">
	import { niceScale, stackedAreas, type Day } from '../chart.js';
	import { formatNumber } from '../format.js';

	interface Props {
		series: Day[];
		/** Read by screen readers instead of the drawing. */
		description: string;
		/** A dashed line on one day, e.g. when an alert was raised. */
		marker?: { day: string; label: string } | null;
	}

	let { series, description, marker = null }: Props = $props();

	// Drawn at the width it is shown, so that the labels keep their size on a phone.
	let shown = $state(760);
	const width = $derived(Math.max(shown, 300));
	const box = $derived({ left: 44, top: 10, width: width - 52, height: 194 });
	const scale = $derived(
		niceScale(Math.max(0, ...series.map((day) => day.negative + day.neutral + day.positive)))
	);
	const areas = $derived(stackedAreas(series, box, scale.max));
	const last = $derived(Math.max(series.length - 1, 1));
	const x = (index: number) => box.left + (index * box.width) / last;
	const y = (value: number) => box.top + box.height - (value / scale.max) * box.height;

	const labels = $derived.by(() => {
		const end = series.length - 1;
		const marks =
			width < 480 ? [0, Math.round(end / 2), end] : [0, Math.round(end / 3), Math.round((2 * end) / 3), end];
		const indexes = [...new Set(marks)];
		return indexes.map((index) => ({
			index,
			text: index === end ? "aujourd'hui" : `il y a ${end - index} j`,
			anchor: index === 0 ? 'start' : index === end ? 'end' : 'middle'
		}));
	});
	const markerIndex = $derived(marker ? series.findIndex((day) => day.day === marker.day) : -1);
	const markerOnLeft = $derived(markerIndex < series.length / 3);
</script>

<div bind:clientWidth={shown}>
	<svg viewBox="0 0 {width} 230" class="block h-auto w-full" role="img" aria-label={description}>
		<g class="stroke-rule" stroke-width="1">
			{#each scale.ticks as tick (tick)}
				<line x1={box.left} x2={box.left + box.width} y1={y(tick)} y2={y(tick)} />
			{/each}
		</g>
		<g class="fill-muted text-xs" text-anchor="end">
			{#each scale.ticks as tick (tick)}
				<text x={box.left - 6} y={y(tick) + 4}>{formatNumber(tick)}</text>
			{/each}
		</g>
		<path d={areas.neutral} class="fill-sand" />
		<path d={areas.positive} class="fill-leaf" />
		<path d={areas.negative} class="fill-clay" />
		{#if marker && markerIndex >= 0}
			<line
				x1={x(markerIndex)}
				x2={x(markerIndex)}
				y1={box.top}
				y2={box.top + box.height}
				class="stroke-ink"
				stroke-dasharray="4 4"
			/>
			<text
				x={x(markerIndex) + (markerOnLeft ? 6 : -6)}
				y={box.top + 16}
				text-anchor={markerOnLeft ? 'start' : 'end'}
				class="fill-ink text-[13px]">{marker.label}</text
			>
		{/if}
		<g class="fill-muted text-xs">
			{#each labels as label (label.index)}
				<text x={x(label.index)} y="222" text-anchor={label.anchor}>{label.text}</text>
			{/each}
		</g>
	</svg>
</div>
