<!-- One conversation: where it was found, a summary, what the analysis made of it, the figures, the article. -->
<script lang="ts">
	import type { Mention } from '@yimba/api';
	import {
		EMOTIONS,
		Icon,
		SENTIMENTS,
		StackedBar,
		formatMoment,
		formatShare,
		languageLabel,
		summarize
	} from '@yimba/ui';
	import CopyLink from './CopyLink.svelte';
	import MentionMetrics from './MentionMetrics.svelte';
	import { originOf, webAddress } from './mention.js';

	interface Props {
		mention: Mention;
		/** voice: the short card of the home page. */
		variant?: 'voice' | 'full';
		class?: string;
	}

	let { mention, variant = 'full', class: className = '' }: Props = $props();

	const sentiment = $derived(SENTIMENTS[mention.sentiment]);
	const original = $derived(webAddress(mention.url));
	const scores = $derived(mention.sentiment_scores);
</script>

<article
	class="flex min-w-0 flex-col rounded-card bg-white {variant === 'voice'
		? 'gap-2.5 p-4 md:gap-3 md:p-5'
		: 'gap-3 p-5'} {className}"
>
	<div class="flex items-center {variant === 'voice' ? 'gap-2.5' : 'gap-3'}">
		<span
			class="flex shrink-0 items-center justify-center rounded-full {variant === 'voice'
				? 'size-9.5 md:size-10'
				: 'size-11'} {sentiment.tone}"
			aria-hidden="true"
		>
			<Icon name="person" size={24} class={sentiment.avatar} />
		</span>
		<div class="min-w-0 flex-1 leading-tight">
			<div class="font-bold">{originOf(mention)}</div>
			<div class="text-sm text-muted">
				{#if variant === 'full'}{languageLabel(mention.language)} ·{/if}
				<time datetime={mention.published_at}>{formatMoment(mention.published_at)}</time>
			</div>
		</div>
		<!-- On a phone the short card shows the sentiment here, like the full one. -->
		<span class="tag {sentiment.tone} {variant === 'voice' ? 'md:hidden' : ''}">{sentiment.label}</span>
	</div>

	<p
		class="max-w-[62ch] leading-normal break-words whitespace-pre-line {variant === 'voice'
			? 'line-clamp-4 md:text-[17px]'
			: 'line-clamp-4 text-lg'}"
	>
		{summarize(mention.text, variant === 'voice' ? 160 : 220)}
	</p>

	{#if variant === 'voice'}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
			<span class="tag hidden md:inline-flex {sentiment.tone}">{sentiment.label}</span>
			{@render emotionTag()}
		</div>
		<MentionMetrics {mention} />
	{:else}
		<div class="flex flex-col gap-1.5">
			<StackedBar negative={scores.negative} neutral={scores.neutral} positive={scores.positive} />
			<p class="text-[13px] text-muted">
				Analyse : {formatShare(scores.negative)} négatif, {formatShare(scores.neutral)} neutre, {formatShare(
					scores.positive
				)} positif.
			</p>
		</div>
		<MentionMetrics {mention} />
		<div class="flex flex-wrap items-center justify-between gap-2">
			{@render emotionTag()}
			{#if original}
				<div class="flex flex-wrap gap-2">
					<CopyLink url={original} />
					<a
						href={original}
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-soft min-h-11 px-4 text-sm"
					>
						Lire l'article <Icon name="external" size={16} /><span class="sr-only">(nouvel onglet)</span>
					</a>
				</div>
			{/if}
		</div>
	{/if}
</article>

{#snippet emotionTag()}
	<span class="tag bg-lilac font-semibold {mention.emotion ? '' : 'text-muted'}">
		{mention.emotion ? EMOTIONS[mention.emotion].label : 'Sans émotion nette'}
	</span>
{/snippet}
