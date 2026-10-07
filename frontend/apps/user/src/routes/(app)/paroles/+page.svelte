<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, describe } from '@yimba/api';
	import {
		EMOTIONS,
		Icon,
		LANGUAGES,
		Notice,
		SENTIMENTS,
		SOURCES,
		formatDate,
		formatNumber,
		plural
	} from '@yimba/ui';
	import MentionCard from '#lib/MentionCard.svelte';
	import { PERIODS, withQuery } from '#lib/watch.js';

	let { data } = $props();

	// "Voir plus" appends the next pages; other filters bring new data, and the list starts again from it.
	let items = $derived(data.listing?.mentions.items ?? []);
	let loadedPages = $derived(1);
	let busy = $state(false);
	let error = $state('');

	async function more() {
		const listing = data.listing;
		if (!listing) return;
		busy = true;
		error = '';
		try {
			const next = await api.watches.mentions(listing.watch.id, {
				...listing.filters,
				...listing.window,
				page: loadedPages + 1,
				size: listing.pageSize
			});
			// New conversations shift the pages: skip the ones already shown.
			const shown = new Set(items.map((mention) => mention.id));
			items = [...items, ...next.items.filter((mention) => !shown.has(mention.id))];
			loadedPages += 1;
		} catch (caught) {
			error = describe(caught);
		} finally {
			busy = false;
		}
	}

	/** This address with some parameters changed; null removes one. */
	function changed(changes: Record<string, string | null>): string {
		const params = new URLSearchParams(page.url.search);
		for (const [key, value] of Object.entries(changes)) {
			if (value === null) params.delete(key);
			else params.set(key, value);
		}
		return `?${params}`;
	}

	const SENTIMENT_TABS = [
		{ value: null, label: 'Toutes' },
		{ value: 'negative', label: SENTIMENTS.negative.plural },
		{ value: 'positive', label: SENTIMENTS.positive.plural },
		{ value: 'neutral', label: SENTIMENTS.neutral.plural }
	] as const;
</script>

<svelte:head>
	<title>Paroles · Yimba</title>
</svelte:head>

{#if !data.listing}
	<div class="card flex flex-col items-start gap-3">
		<h1 class="text-3xl font-bold">Les paroles des gens</h1>
		<p class="text-ink-soft">Créez d'abord une veille : Yimba saura quoi écouter.</p>
		<a href={resolve('/(app)/veilles/nouvelle')} class="btn btn-primary">Créer une veille</a>
	</div>
{:else}
	{@const { watch, filters, totals, days, window, explicitWindow, mentions, pageSize } = data.listing}
	{@const counted = !filters.emotion && !filters.q}
	{@const groups = [
		{
			title: 'Où',
			param: 'source',
			current: filters.source ?? null,
			options: [
				{ value: null, label: 'Partout' },
				...watch.sources.map((source) => ({ value: source, label: SOURCES[source] }))
			]
		},
		{
			title: 'Langue',
			param: 'langue',
			current: filters.language ?? null,
			options: [
				{ value: null, label: 'Toutes' },
				...['fr', 'nouchi', 'en'].map((code) => ({ value: code, label: LANGUAGES[code] }))
			]
		},
		{
			title: 'Émotion',
			param: 'emotion',
			current: filters.emotion ?? null,
			options: [
				{ value: null, label: 'Toutes' },
				...Object.entries(EMOTIONS).map(([value, emotion]) => ({ value, label: emotion.label }))
			]
		}
	]}

	<div class="flex flex-col gap-4.5">
		<header class="flex flex-col gap-1">
			<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">
				Les paroles des gens
			</h1>
			<p class="text-[17px] text-muted">
				{plural(mentions.total, 'conversation')} sur « {watch.name} »
				{explicitWindow && window.end
					? `entre le ${formatDate(window.start)} et le ${formatDate(window.end)}`
					: `ces ${days} derniers jours`}. Toutes les personnes sont anonymes.
			</p>
		</header>

		<nav class="flex flex-wrap gap-2" aria-label="Ressenti">
			{#each SENTIMENT_TABS as tab (tab.label)}
				{@const count = tab.value ? totals[tab.value] : totals.total}
				<a
					href={changed({ ressenti: tab.value })}
					class="tab"
					aria-current={(filters.sentiment ?? null) === tab.value ? 'true' : undefined}
				>
					{tab.label}
					{#if counted}<span class="font-semibold opacity-80">{formatNumber(count)}</span>{/if}
				</a>
			{/each}
		</nav>

		<div class="flex flex-wrap items-start gap-4.5">
			<section class="flex min-w-0 flex-[2_1_480px] flex-col gap-3.5" aria-label="Conversations">
				{#each items as mention (mention.id)}
					<MentionCard {mention} />
				{:else}
					<div class="card flex flex-col items-start gap-3">
						<p class="text-lg">Aucune conversation ne correspond à ces filtres.</p>
						<a href={withQuery(resolve('/(app)/paroles'), { veille: watch.id })} class="btn btn-ghost">
							Retirer les filtres
						</a>
					</div>
				{/each}

				{#if error}
					<Notice tone="danger">{error}</Notice>
				{/if}
				{#if items.length}
					<div class="flex flex-col items-center gap-2.5 pt-1.5">
						<p class="text-sm text-muted tabular-nums" aria-live="polite">
							{formatNumber(items.length)}
							{items.length > 1 ? 'conversations affichées' : 'conversation affichée'} sur {formatNumber(
								mentions.total
							)}
						</p>
						{#if items.length < mentions.total}
							{@const next = Math.min(pageSize, mentions.total - items.length)}
							<button type="button" class="btn btn-primary px-6.5" disabled={busy} onclick={more}>
								{busy ? 'Chargement…' : `Voir ${next} ${next > 1 ? 'conversations' : 'conversation'} de plus`}
							</button>
						{:else if mentions.total > pageSize}
							<p class="text-sm text-muted">Toutes les conversations sont affichées.</p>
						{/if}
					</div>
				{/if}
			</section>

			<aside
				class="order-first flex min-w-0 flex-[1_1_280px] flex-col gap-3.5 lg:sticky lg:top-24 lg:order-0 lg:max-h-[calc(100dvh-7rem)] lg:self-start lg:overflow-y-auto"
				aria-label="Filtres"
			>
				<div class="flex flex-col gap-3.5 rounded-card bg-white p-5">
					<h2 class="text-xl font-semibold">Affiner</h2>
					<form
						method="get"
						class="flex min-h-11.5 items-center gap-2.5 rounded-field bg-lilac px-4 md:hidden"
						role="search"
					>
						<Icon name="search" size={18} class="text-muted" />
						<label for="mention-search" class="sr-only">Chercher dans les conversations</label>
						<input
							id="mention-search"
							name="q"
							type="search"
							value={filters.q ?? ''}
							placeholder="Un mot, un lieu"
							class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted"
						/>
						{#each [...page.url.searchParams].filter(([key]) => key !== 'q') as [key, value] (key)}
							<input type="hidden" name={key} {value} />
						{/each}
					</form>

					{#each groups as group (group.param)}
						<div class="flex flex-col gap-2">
							<span class="text-sm font-bold text-muted">{group.title}</span>
							<div class="flex flex-wrap gap-2">
								{#each group.options as option (option.label)}
									<a
										href={changed({ [group.param]: option.value })}
										class="chip"
										aria-current={group.current === option.value ? 'true' : undefined}>{option.label}</a
									>
								{/each}
							</div>
						</div>
					{/each}

					<div class="flex flex-col gap-2">
						<span class="text-sm font-bold text-muted">Période</span>
						<div class="flex flex-wrap gap-2">
							{#if explicitWindow}
								<span class="chip" aria-current="true">Fenêtre de l'alerte</span>
							{/if}
							{#each PERIODS as option (option)}
								<a
									href={changed({ periode: String(option), debut: null, fin: null })}
									class="chip"
									aria-current={!explicitWindow && option === days ? 'true' : undefined}>{option} jours</a
								>
							{/each}
						</div>
					</div>
				</div>

				<div class="flex flex-col gap-2 rounded-card bg-sun-soft p-5">
					<h2 class="text-lg font-semibold text-sun-dark">Lire avant de conclure</h2>
					<p class="text-[15px] text-sun-text">
						Le nouchi et le français ivoirien ne ressemblent pas au français des manuels : l'analyse peut se
						tromper sur le ressenti ou l'émotion. Lisez l'original avant de citer une conversation.
					</p>
				</div>
			</aside>
		</div>
	</div>
{/if}
