<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, describe, type Watch } from '@yimba/api';
	import {
		Icon,
		Notice,
		SOURCES,
		SOURCE_ORDER,
		formatDate,
		formatNumber,
		formatShare,
		frequencyLabel,
		percent,
		plural
	} from '@yimba/ui';
	import { withQuery } from '#lib/watch.js';

	let { data } = $props();

	const TABS = [
		{ value: null, label: 'Toutes', count: () => data.counts.all },
		{ value: 'actives', label: 'Actives', count: () => data.counts.actives },
		{ value: 'pause', label: 'En pause', count: () => data.counts.pause }
	] as const;

	const VIEWS = [
		{ value: null, label: 'Liste', icon: 'list' },
		{ value: 'cartes', label: 'Cartes', icon: 'home' }
	] as const;

	const SORTS = [
		{ value: 'created', param: null, label: 'Date', icon: 'calendar' },
		{ value: 'name', param: 'nom', label: 'Nom', icon: 'az' }
	] as const;
	const orderLabel = $derived(
		data.sort === 'name'
			? data.order === 'asc'
				? 'A → Z'
				: 'Z → A'
			: data.order === 'asc'
				? 'Plus anciennes d’abord'
				: 'Plus récentes d’abord'
	);

	let pending = $state<string | null>(null);
	let error = $state('');

	/** This address with some parameters changed; null removes one. */
	function changed(changes: Record<string, string | null>): string {
		const params = new URLSearchParams(page.url.search);
		for (const [key, value] of Object.entries(changes)) {
			if (value === null) params.delete(key);
			else params.set(key, value);
		}
		const search = params.toString();
		return search ? `?${search}` : page.url.pathname;
	}

	async function toggle(watch: Watch) {
		pending = watch.id;
		error = '';
		try {
			await api.watches.update(watch.id, { active: !watch.active });
			await invalidate('yimba:watches');
		} catch (caught) {
			error = describe(caught);
		} finally {
			pending = null;
		}
	}

	const items = $derived(data.page.items);
	const first = $derived((data.page.page - 1) * data.page.size + 1);
	const last = $derived(first + items.length - 1);
	// Page numbers: the first, the last and two on each side of the current one, with gaps shown as "…".
	const numbers = $derived.by(() => {
		const current = data.page.page;
		const wanted = new Set([1, data.pages, ...[-2, -1, 0, 1, 2].map((shift) => current + shift)]);
		const sorted = [...wanted].filter((n) => n >= 1 && n <= data.pages).sort((a, b) => a - b);
		return sorted.flatMap((n, index) => (index && n - sorted[index - 1] > 1 ? [0, n] : [n]));
	});
</script>

<svelte:head>
	<title>Mes veilles · Yimba</title>
</svelte:head>

<div class="flex flex-col gap-5">
	<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
		<div class="flex flex-col gap-1.5">
			<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">Mes veilles</h1>
			<p class="max-w-[62ch] text-[17px] text-muted">
				{plural(data.counts.all, 'veille')}, dont {plural(data.counts.actives, 'active')}. Une veille écoute
				un sujet : les mots, les sources et le moment où Yimba vous prévient.
			</p>
		</div>
		<a href={resolve('/(app)/veilles/nouvelle')} class="btn btn-primary shrink-0">
			<Icon name="plus" size={18} /> Nouvelle veille
		</a>
	</header>

	{#if data.counts.all > 0}
		<div class="flex flex-col gap-3">
			<div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
				<nav class="flex flex-wrap gap-2" aria-label="État des veilles">
					{#each TABS as tab (tab.label)}
						<a
							href={changed({ etat: tab.value, page: null })}
							class="tab"
							aria-current={data.filter === tab.value ? 'true' : undefined}
						>
							{tab.label} · {formatNumber(tab.count())}
						</a>
					{/each}
				</nav>
				<nav class="flex rounded-field bg-white p-1" aria-label="Affichage">
					{#each VIEWS as option (option.label)}
						{@const current = (data.view === 'cartes') === (option.value === 'cartes')}
						<a
							href={changed({ vue: option.value, page: null })}
							aria-current={current ? 'true' : undefined}
							class="flex min-h-9.5 items-center gap-2 rounded-field px-3 text-sm font-bold no-underline {current
								? 'bg-indigo-soft text-indigo-deep'
								: 'text-muted hover:text-ink'}"
						>
							<Icon name={option.icon} size={16} />{option.label}
						</a>
					{/each}
				</nav>
			</div>

			<div class="flex flex-wrap items-center gap-x-3 gap-y-2.5">
				<form method="get" role="search" class="flex min-w-0 flex-[1_1_220px] sm:max-w-xs">
					{#each [['etat', data.filter], ['vue', data.view === 'cartes' ? 'cartes' : null], ['tri', data.sort === 'name' ? 'nom' : null], ['ordre', data.order === 'asc' ? 'asc' : null]] as const as [name, value] (name)}
						{#if value}<input type="hidden" {name} {value} />{/if}
					{/each}
					<label class="flex min-h-11.5 w-full items-center gap-2.5 rounded-field bg-white px-4">
						<Icon name="search" size={18} class="text-muted" />
						<span class="sr-only">Chercher une veille par son nom</span>
						<input
							name="q"
							type="search"
							value={data.search}
							placeholder="Chercher une veille"
							class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted"
						/>
					</label>
				</form>
				<div class="flex items-center gap-2">
					<nav class="flex rounded-field bg-white p-1" aria-label="Trier par">
						{#each SORTS as option (option.label)}
							{@const current = data.sort === option.value}
							<a
								href={changed({ tri: option.param, page: null })}
								aria-current={current ? 'true' : undefined}
								title="Trier par {option.label.toLowerCase()}"
								class="flex min-h-9.5 items-center gap-2 rounded-field px-3 text-sm font-bold no-underline {current
									? 'bg-indigo-soft text-indigo-deep'
									: 'text-muted hover:text-ink'}"
							>
								<Icon name={option.icon} size={16} />{option.label}
							</a>
						{/each}
					</nav>
					<a
						href={changed({ ordre: data.order === 'asc' ? null : 'asc', page: null })}
						class="flex min-h-11.5 items-center gap-2 rounded-field bg-white px-3.5 text-sm font-bold text-ink no-underline hover:text-indigo"
						title="Inverser l'ordre"
						aria-label="{orderLabel} : inverser l'ordre"
					>
						<Icon name={data.order === 'asc' ? 'sort-asc' : 'sort-desc'} size={18} />
						{orderLabel}
					</a>
				</div>
			</div>
		</div>
	{/if}

	{#if error}
		<Notice tone="danger">{error}</Notice>
	{/if}

	{#if items.length}
		{#if data.view === 'cartes'}
			<ul class="grid gap-4 xl:grid-cols-2">
				{#each items as watch (watch.id)}
					{@const summary = data.summaries[watch.id]}
					{@const openAlerts = summary?.openAlerts ?? 0}
					<li class="flex min-w-0 flex-col rounded-card bg-white">
						<div class="flex flex-col gap-3 p-5.5 pb-4">
							<div class="flex items-start justify-between gap-3">
								<h2
									class="line-clamp-2 min-w-0 text-[21px] leading-snug font-semibold [overflow-wrap:anywhere]"
								>
									{watch.name}
								</h2>
								<span
									class="tag mt-0.5 shrink-0 {watch.active
										? 'bg-leaf-soft text-leaf-ink'
										: 'bg-sand-soft text-sand-ink'}"
								>
									{watch.active ? 'Active' : 'En pause'}
								</span>
							</div>
							<ul class="flex flex-wrap gap-1.5" aria-label="Mots suivis">
								{#each watch.keywords as keyword (keyword)}
									<li class="tag bg-indigo-soft text-indigo-deep">{keyword}</li>
								{/each}
							</ul>
						</div>

						<dl
							class="mx-5.5 grid grid-cols-3 divide-x divide-rule rounded-field bg-lilac py-3 text-center tabular-nums"
						>
							<div class="px-2">
								<dd class="figure text-[26px] leading-tight">
									{summary ? formatNumber(summary.totals.total) : '—'}
								</dd>
								<dt class="text-[13px] text-muted">conversations, {data.days} j</dt>
							</div>
							<div class="px-2">
								<dd class="figure text-[26px] leading-tight">
									{summary?.totals.total ? formatShare(summary.totals.negative_share) : '—'}
								</dd>
								<dt class="text-[13px] text-muted">de négatif</dt>
							</div>
							<div class="px-2">
								<dd class="figure text-[26px] leading-tight {openAlerts ? 'text-clay-ink' : ''}">
									{formatNumber(openAlerts)}
								</dd>
								<dt class="text-[13px] text-muted">
									{openAlerts > 1 ? 'alertes à traiter' : 'alerte à traiter'}
								</dt>
							</div>
						</dl>

						<p class="px-5.5 pt-3.5 text-sm text-muted">
							{SOURCE_ORDER.filter((source) => watch.sources.includes(source))
								.map((source) => SOURCES[source])
								.join(', ')}
							<span aria-hidden="true">·</span>
							{frequencyLabel(watch.frequency_minutes).toLowerCase()}
							<span aria-hidden="true">·</span>
							alerte à {percent(watch.alert_negative_share)} % de négatif, dès {plural(
								watch.alert_min_mentions,
								'conversation'
							)}
							<span aria-hidden="true">·</span>
							créée le {formatDate(watch.created_at)}
						</p>

						<div class="mt-auto grid grid-cols-2 gap-2 p-5.5 pt-4">
							<a
								href={withQuery(resolve('/(app)'), { veille: watch.id })}
								class="btn btn-primary min-h-11 px-3 text-sm"
							>
								Tableau de bord
							</a>
							<a
								href={withQuery(resolve('/(app)/paroles'), { veille: watch.id })}
								class="btn btn-soft min-h-11 px-3 text-sm"
							>
								Conversations
							</a>
							<a
								href={resolve('/(app)/veilles/[id]', { id: watch.id })}
								class="btn btn-ghost min-h-11 px-3 text-sm"
							>
								Réglages
							</a>
							<button
								type="button"
								class="btn btn-ghost min-h-11 px-3 text-sm"
								disabled={pending === watch.id}
								onclick={() => toggle(watch)}
							>
								{watch.active ? 'Mettre en pause' : 'Reprendre'}
							</button>
						</div>
					</li>
				{/each}
			</ul>
		{:else}
			<div class="overflow-hidden rounded-card bg-white">
				<div
					class="hidden grid-cols-[minmax(0,1fr)_96px_88px_130px_100px_280px] items-center gap-x-4 border-b border-rule px-5.5 py-3 text-sm font-bold text-muted xl:grid"
					aria-hidden="true"
				>
					<span>Veille</span>
					<span>Créée le</span>
					<span class="text-right">Conversations</span>
					<span>Négatif</span>
					<span class="text-right">Alertes</span>
					<span class="text-right">Actions</span>
				</div>
				<ul class="divide-y divide-rule">
					{#each items as watch (watch.id)}
						{@const summary = data.summaries[watch.id]}
						{@const openAlerts = summary?.openAlerts ?? 0}
						{@const share = summary?.totals.total ? summary.totals.negative_share : null}
						<li
							class="grid gap-x-4 gap-y-3 px-5.5 py-4 xl:grid-cols-[minmax(0,1fr)_96px_88px_130px_100px_280px] xl:items-center"
						>
							<div class="flex min-w-0 flex-col gap-1">
								<div class="flex items-center gap-2.5">
									<span
										class="size-2.5 shrink-0 rounded-full {watch.active ? 'bg-leaf' : 'bg-sand'}"
										aria-hidden="true"
									></span>
									<a
										href={withQuery(resolve('/(app)'), { veille: watch.id })}
										class="min-w-0 truncate text-lg font-semibold text-ink no-underline hover:text-indigo"
										title={watch.name}>{watch.name}</a
									>
									<span
										class="tag shrink-0 {watch.active
											? 'bg-leaf-soft text-leaf-ink'
											: 'bg-sand-soft text-sand-ink'}"
									>
										{watch.active ? 'Active' : 'En pause'}
									</span>
								</div>
								<p class="truncate text-sm text-muted" title={watch.keywords.join(', ')}>
									{watch.keywords.join(' · ')}
								</p>
								<p class="truncate text-[13px] text-muted">
									{SOURCE_ORDER.filter((source) => watch.sources.includes(source))
										.map((source) => SOURCES[source])
										.join(', ')}
									<span aria-hidden="true">·</span>
									{frequencyLabel(watch.frequency_minutes).toLowerCase()}
									<span aria-hidden="true">·</span>
									alerte à {percent(watch.alert_negative_share)} %, dès {watch.alert_min_mentions}
								</p>
							</div>

							<div class="grid grid-cols-2 gap-3 tabular-nums sm:grid-cols-4 xl:contents">
								<div class="text-sm xl:text-muted">
									<span class="text-[13px] text-muted xl:sr-only">Créée le</span>
									<div>{formatDate(watch.created_at)}</div>
								</div>
								<div class="xl:text-right">
									<span class="text-[13px] text-muted xl:sr-only">Conversations</span>
									<div class="figure text-xl">{summary ? formatNumber(summary.totals.total) : '—'}</div>
								</div>
								<div>
									<span class="text-[13px] text-muted xl:sr-only">Négatif</span>
									<div class="flex items-center gap-2.5">
										<span class="figure w-12 text-xl">{share === null ? '—' : formatShare(share)}</span>
										<span
											class="hidden h-2 flex-1 overflow-hidden rounded-[4px] bg-track xl:block"
											aria-hidden="true"
										>
											<span class="block h-full bg-clay" style:width="{(share ?? 0) * 100}%"></span>
										</span>
									</div>
								</div>
								<div class="xl:text-right">
									<span class="text-[13px] text-muted xl:sr-only">Alertes à traiter</span>
									<div>
										{#if openAlerts}
											<a
												href={withQuery(resolve('/(app)/alertes'), { veille: watch.id })}
												class="tag bg-sun-soft text-sun-ink no-underline"
											>
												{openAlerts} à traiter
											</a>
										{:else}
											<span class="text-muted">Aucune</span>
										{/if}
									</div>
								</div>
							</div>

							<div class="grid grid-cols-3 gap-2 xl:justify-self-end">
								<a
									href={withQuery(resolve('/(app)/paroles'), { veille: watch.id })}
									class="btn btn-soft min-h-10 px-2 text-sm xl:w-[88px]"
								>
									Paroles
								</a>
								<a
									href={resolve('/(app)/veilles/[id]', { id: watch.id })}
									class="btn btn-ghost min-h-10 px-2 text-sm xl:w-[88px]"
								>
									Réglages
								</a>
								<button
									type="button"
									class="btn btn-ghost min-h-10 px-2 text-sm xl:w-[88px]"
									disabled={pending === watch.id}
									onclick={() => toggle(watch)}
								>
									{watch.active ? 'Pause' : 'Reprendre'}
								</button>
							</div>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if data.pages > 1}
			<nav class="flex flex-wrap items-center justify-between gap-3" aria-label="Pages de veilles">
				<p class="text-sm text-muted tabular-nums" aria-live="polite">
					Veilles {formatNumber(first)} à {formatNumber(last)} sur {formatNumber(data.page.total)}
				</p>
				<ul class="flex flex-wrap items-center gap-1.5">
					<li>
						{#if data.page.page > 1}
							<a
								href={changed({ page: String(data.page.page - 1) })}
								class="btn btn-ghost min-h-11 px-4 text-sm"
							>
								Précédente
							</a>
						{:else}
							<span class="btn btn-ghost min-h-11 px-4 text-sm" aria-disabled="true">Précédente</span>
						{/if}
					</li>
					{#each numbers as number, index (index)}
						<li class={number ? '' : 'hidden sm:block'}>
							{#if number === 0}
								<span class="px-1 text-muted" aria-hidden="true">…</span>
							{:else}
								<a
									href={changed({ page: number === 1 ? null : String(number) })}
									class="tab min-w-11 justify-center px-3"
									aria-current={number === data.page.page ? 'page' : undefined}
									aria-label="Page {number}">{number}</a
								>
							{/if}
						</li>
					{/each}
					<li>
						{#if data.page.page < data.pages}
							<a
								href={changed({ page: String(data.page.page + 1) })}
								class="btn btn-ghost min-h-11 px-4 text-sm"
							>
								Suivante
							</a>
						{:else}
							<span class="btn btn-ghost min-h-11 px-4 text-sm" aria-disabled="true">Suivante</span>
						{/if}
					</li>
				</ul>
			</nav>
		{/if}
	{:else}
		<div class="card flex flex-col items-start gap-3">
			{#if data.counts.all === 0}
				<p class="text-lg">Vous n'avez pas encore de veille.</p>
				<a href={resolve('/(app)/veilles/nouvelle')} class="btn btn-primary">Créer ma première veille</a>
			{:else}
				<p class="text-lg">Aucune veille ne correspond.</p>
				<a href={resolve('/(app)/veilles')} class="btn btn-ghost">Voir toutes les veilles</a>
			{/if}
		</div>
	{/if}
</div>
