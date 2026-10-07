<!-- Conversations split by source or by language, each row with its share of negative, neutral and positive. -->
<script lang="ts">
	import type { Counts } from '@yimba/api';
	import { StackedBar, formatNumber, formatShare } from '@yimba/ui';

	interface Props {
		title: string;
		description?: string;
		buckets: { key: string; counts: Counts }[];
		label: (key: string) => string;
		/** compact (phone): the three most negative rows, without the counts. */
		compact?: boolean;
		class?: string;
	}

	let { title, description, buckets, label, compact = false, class: className = '' }: Props = $props();

	const rows = $derived(
		compact
			? [...buckets].sort((a, b) => b.counts.negative_share - a.counts.negative_share).slice(0, 3)
			: [...buckets].sort((a, b) => b.counts.total - a.counts.total)
	);
</script>

<section
	class="flex min-w-0 flex-col rounded-card bg-white {compact
		? 'gap-3 p-4.5'
		: 'flex-[1_1_420px] gap-3.5 p-6'} {className}"
>
	<div>
		<h2 class="font-semibold {compact ? 'text-xl' : 'mb-1 text-[22px]'}">{title}</h2>
		{#if description}<p class="text-sm text-muted">{description}</p>{/if}
	</div>
	{#each rows as row (row.key)}
		<div class="flex flex-col gap-1">
			<div class="flex justify-between gap-3 tabular-nums {compact ? 'text-[15px]' : ''}">
				<span class="font-bold">{label(row.key)}</span>
				<span class="whitespace-nowrap text-muted">
					{#if !compact}{formatNumber(row.counts.total)} ·{/if}
					{formatShare(row.counts.negative_share)} négatif
				</span>
			</div>
			<StackedBar
				negative={row.counts.negative}
				neutral={row.counts.neutral}
				positive={row.counts.positive}
			/>
		</div>
	{:else}
		<p class="text-muted">Rien sur cette période.</p>
	{/each}
</section>
