<!-- One conversation. Authors stay anonymous: a short pseudonym tells the voices apart. -->
<script lang="ts">
	import type { Mention } from '@yimba/api';
	import { EMOTIONS, Icon, SENTIMENTS, formatAgo, languageLabel } from '@yimba/ui';
	import CopyLink from './CopyLink.svelte';
	import MentionMetrics from './MentionMetrics.svelte';
	import { authorLabel, originOf, webAddress } from './mention.js';

	interface Props {
		mention: Mention;
		/** voice: the short card of the home page. */
		variant?: 'voice' | 'full';
		class?: string;
		/** Opens the conversation next to the list (full variant). */
		onselect?: (mention: Mention) => void;
		selected?: boolean;
	}

	let { mention, variant = 'full', class: className = '', onselect, selected = false }: Props = $props();

	const sentiment = $derived(SENTIMENTS[mention.sentiment]);
	const original = $derived(webAddress(mention.url));
</script>

<article
	class="flex min-w-0 flex-col rounded-card bg-white {variant === 'voice'
		? 'gap-2.5 p-4 md:gap-3 md:p-5'
		: 'gap-3 p-5'} {selected ? 'outline-2 outline-indigo' : ''} {className}"
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
			<div class="font-bold">
				{variant === 'voice' ? 'Personne anonyme' : authorLabel(mention.author_ref)}
			</div>
			<div class="text-sm text-muted">
				{originOf(mention)} ·
				{#if variant === 'full'}{languageLabel(mention.language)} ·{/if}
				<time datetime={mention.published_at}>{formatAgo(mention.published_at)}</time>
			</div>
		</div>
		<!-- On a phone the short card shows the sentiment here, like the full one. -->
		<span class="tag {sentiment.tone} {variant === 'voice' ? 'md:hidden' : ''}">{sentiment.label}</span>
	</div>

	<p
		class="max-w-[62ch] leading-normal break-words whitespace-pre-line {variant === 'voice'
			? 'line-clamp-5 md:text-[17px]'
			: 'line-clamp-8 text-lg'}"
	>
		{mention.text}
	</p>

	{#if variant === 'voice'}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
			<span class="tag hidden md:inline-flex {sentiment.tone}">{sentiment.label}</span>
			{@render emotionTag()}
		</div>
		<MentionMetrics {mention} />
	{:else}
		<MentionMetrics {mention} />
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex flex-wrap gap-2">
				{@render emotionTag()}
				<span class="tag bg-lilac font-semibold">{languageLabel(mention.language)}</span>
			</div>
			<div class="flex flex-wrap gap-2">
				{#if original}<CopyLink url={original} />{/if}
				{#if onselect}
					<button
						type="button"
						class="btn min-h-11 px-4 text-sm {selected ? 'btn-primary' : 'btn-soft'}"
						aria-pressed={selected}
						onclick={() => onselect(mention)}
					>
						{selected ? 'Ouverte à côté' : 'Ouvrir'}
					</button>
				{/if}
			</div>
		</div>
	{/if}
</article>

{#snippet emotionTag()}
	<span class="tag bg-lilac font-semibold {mention.emotion ? '' : 'text-muted'}">
		{mention.emotion ? EMOTIONS[mention.emotion].label : 'Sans émotion nette'}
	</span>
{/snippet}
