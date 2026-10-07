<!-- The conversation opened next to the list: a summary, the whole text, where it comes from, the figures; the link stays behind a button. -->
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
	import { authorLabel, originOf, webAddress } from './mention.js';

	let { mention, onclose }: { mention: Mention; onclose: () => void } = $props();

	const sentiment = $derived(SENTIMENTS[mention.sentiment]);
	const address = $derived(webAddress(mention.url));
	const scores = $derived(mention.sentiment_scores);
	const summary = $derived(summarize(mention.text, 220));
	const clean = $derived(summarize(mention.text, Number.MAX_SAFE_INTEGER));
</script>

<section class="flex flex-col gap-4 rounded-card bg-white p-5" aria-labelledby="detail-title">
	<div class="flex items-start justify-between gap-3">
		<div class="flex flex-col leading-tight">
			<h2 id="detail-title" class="text-xl font-semibold">La conversation</h2>
			<span class="text-sm text-muted">{formatMoment(mention.published_at)}</span>
		</div>
		<button
			type="button"
			class="flex size-11 shrink-0 items-center justify-center rounded-field text-xl hover:bg-haze"
			aria-label="Fermer la conversation"
			onclick={onclose}>×</button
		>
	</div>

	<div class="flex flex-col gap-2">
		<p class="text-[17px] leading-normal break-words">
			{#if summary !== clean}<span class="font-bold">En bref&nbsp;: </span>{/if}{summary}
		</p>
		{#if summary !== clean}
			<details class="text-[15px]">
				<summary class="cursor-pointer font-bold text-indigo">Lire le texte entier</summary>
				<p class="mt-2 max-h-72 overflow-y-auto leading-normal break-words whitespace-pre-line">
					{mention.text}
				</p>
			</details>
		{/if}
	</div>

	<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[15px]">
		<dt class="text-muted">Trouvée sur</dt>
		<dd class="font-semibold">{originOf(mention)}</dd>
		<dt class="text-muted">Langue</dt>
		<dd class="font-semibold">{languageLabel(mention.language)}</dd>
		<dt class="text-muted">Auteur</dt>
		<dd class="font-semibold">{authorLabel(mention.author_ref)}</dd>
		<dt class="text-muted">Ressenti</dt>
		<dd><span class="tag {sentiment.tone}">{sentiment.label}</span></dd>
		{#if mention.emotion}
			<dt class="text-muted">Émotion</dt>
			<dd class="font-semibold">{EMOTIONS[mention.emotion].label}</dd>
		{/if}
	</dl>

	<div class="flex flex-col gap-1.5">
		<StackedBar negative={scores.negative} neutral={scores.neutral} positive={scores.positive} />
		<p class="text-[13px] text-muted">
			Analyse : {formatShare(scores.negative)} négatif, {formatShare(scores.neutral)} neutre, {formatShare(
				scores.positive
			)} positif. Le nouchi peut tromper l'analyse : lisez le texte.
		</p>
	</div>

	<MentionMetrics {mention} />

	{#if address}
		<div class="flex flex-wrap gap-2 border-t border-rule pt-4">
			<a
				href={address}
				target="_blank"
				rel="noopener noreferrer"
				class="btn btn-primary min-h-11 px-4 text-sm"
			>
				Ouvrir l'article <Icon name="external" size={16} /><span class="sr-only">(nouvel onglet)</span>
			</a>
			<CopyLink url={address} />
		</div>
	{:else}
		<p class="border-t border-rule pt-4 text-sm text-muted">Cette conversation n'a pas de lien d'origine.</p>
	{/if}
</section>
