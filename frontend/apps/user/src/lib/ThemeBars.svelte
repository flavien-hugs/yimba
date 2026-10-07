<!-- The words that come back in the most conversations, each with what people say about it. -->
<script lang="ts">
	import type { Theme } from '@yimba/api';
	import { StackedBar, formatNumber, percent } from '@yimba/ui';

	interface Props {
		themes: Theme[];
		/** compact (phone): the three most negative, without the counts. */
		compact?: boolean;
		class?: string;
	}

	let { themes, compact = false, class: className = '' }: Props = $props();

	const share = (theme: Theme) => theme.negative / Math.max(1, theme.mentions);
	const shown = $derived(compact ? [...themes].sort((a, b) => share(b) - share(a)).slice(0, 3) : themes);
	const capital = (term: string) => term.charAt(0).toUpperCase() + term.slice(1);
</script>

<section
	class="flex min-w-0 flex-col rounded-card bg-white {compact
		? 'gap-3 p-4.5'
		: 'flex-[1_1_420px] gap-3.5 p-6'} {className}"
	aria-labelledby="themes-title-{compact ? 'c' : 'd'}"
>
	<div>
		<h2
			id="themes-title-{compact ? 'c' : 'd'}"
			class="font-semibold {compact ? 'text-xl' : 'mb-1 text-[22px]'}"
		>
			{compact ? 'Ce qui pèse le plus' : 'De quoi on parle'}
		</h2>
		{#if !compact}
			<p class="text-sm text-muted">
				Les mots qui reviennent le plus, avec ce que les gens en pensent. Chaque mot compte une fois par
				conversation.
			</p>
		{/if}
	</div>
	{#each shown as theme (theme.term)}
		<div class="flex flex-col gap-1">
			<div class="flex justify-between gap-3 tabular-nums {compact ? 'text-[15px]' : ''}">
				<span class="font-bold">{capital(theme.term)}</span>
				<span class="whitespace-nowrap text-muted">
					{compact ? '' : `${formatNumber(theme.mentions)} · `}{percent(share(theme))} % négatif
				</span>
			</div>
			<StackedBar negative={theme.negative} neutral={theme.neutral} positive={theme.positive} />
		</div>
	{:else}
		<p class="text-muted">Pas encore assez de conversations pour dégager des sujets.</p>
	{/each}
</section>
