<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
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
		{ value: 'all', label: 'Toutes' },
		{ value: 'active', label: 'Actives' },
		{ value: 'paused', label: 'En pause' }
	] as const;
	let tab = $state<(typeof TABS)[number]['value']>('all');
	let query = $state('');
	let pending = $state<string | null>(null);
	let error = $state('');

	// Accents and case do not matter.
	const fold = (text: string) =>
		text
			.normalize('NFD')
			.replace(/\p{Diacritic}/gu, '')
			.toLowerCase();
	const counts = $derived({
		all: data.watches.length,
		active: data.watches.filter((watch) => watch.active).length,
		paused: data.watches.filter((watch) => !watch.active).length
	});
	const shown = $derived(
		data.watches.filter(
			(watch) =>
				(tab === 'all' || (tab === 'active') === watch.active) &&
				(!query.trim() ||
					[watch.name, ...watch.keywords].some((text) => fold(text).includes(fold(query.trim()))))
		)
	);

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
</script>

<svelte:head>
	<title>Mes veilles · Yimba</title>
</svelte:head>

<div class="flex flex-col gap-4.5">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex flex-col gap-1.5">
			<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">Mes veilles</h1>
			<p class="max-w-[66ch] text-[17px] text-muted">
				{plural(counts.all, 'veille')}, dont {plural(counts.active, 'active')}. Une veille écoute un sujet :
				les mots, les sources et le moment où Yimba vous prévient.
			</p>
		</div>
		<a href={resolve('/(app)/veilles/nouvelle')} class="btn btn-primary">
			<Icon name="plus" size={18} /> Nouvelle veille
		</a>
	</header>

	{#if counts.all > 0}
		<div class="flex flex-wrap items-center gap-3">
			<div class="flex flex-wrap gap-2" role="group" aria-label="État des veilles">
				{#each TABS as option (option.value)}
					<button
						type="button"
						class="tab"
						aria-pressed={tab === option.value}
						onclick={() => (tab = option.value)}
					>
						{option.label} · {formatNumber(counts[option.value])}
					</button>
				{/each}
			</div>
			<label
				class="flex min-h-11.5 flex-[1_1_260px] items-center gap-2.5 rounded-field bg-white px-4 sm:max-w-sm"
			>
				<Icon name="search" size={18} class="text-muted" />
				<span class="sr-only">Chercher une veille</span>
				<input
					type="search"
					placeholder="Chercher une veille ou un mot"
					bind:value={query}
					class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted"
				/>
			</label>
		</div>
	{/if}

	{#if error}
		<Notice tone="danger">{error}</Notice>
	{/if}

	<ul class="flex flex-col gap-3.5">
		{#each shown as watch (watch.id)}
			{@const summary = data.summaries[watch.id]}
			<li class="flex flex-wrap items-start gap-x-6 gap-y-4 rounded-card bg-white p-5.5">
				<div class="flex min-w-0 flex-[2_1_340px] flex-col gap-2.5">
					<div class="flex flex-wrap items-center gap-2.5">
						<h2 class="text-[22px] font-semibold">{watch.name}</h2>
						{#if watch.active}
							<span class="tag bg-leaf-soft text-leaf-ink">Active</span>
						{:else}
							<span class="tag bg-sand-soft text-sand-ink">En pause</span>
						{/if}
						{#if summary?.openAlerts}
							<a
								href={withQuery(resolve('/(app)/alertes'), { veille: watch.id })}
								class="tag bg-sun-soft text-sun-ink no-underline"
							>
								{plural(summary.openAlerts, 'alerte')} à traiter
							</a>
						{/if}
					</div>
					<ul class="flex flex-wrap gap-1.5" aria-label="Mots suivis">
						{#each watch.keywords as keyword (keyword)}
							<li class="tag bg-indigo-soft text-indigo-deep">{keyword}</li>
						{/each}
					</ul>
					<p class="text-sm text-muted">
						{SOURCE_ORDER.filter((source) => watch.sources.includes(source))
							.map((source) => SOURCES[source])
							.join(', ')}
						· {frequencyLabel(watch.frequency_minutes).toLowerCase()} · alerte au-delà de
						{percent(watch.alert_negative_share)} % de négatif, dès {plural(
							watch.alert_min_mentions,
							'conversation'
						)}
						· créée le {formatDate(watch.created_at)}
					</p>
				</div>

				<dl class="flex flex-[1_1_200px] gap-6 tabular-nums">
					<div>
						<dt class="text-sm text-muted">{data.days} jours</dt>
						<dd class="figure text-[28px] leading-tight">
							{summary ? formatNumber(summary.totals.total) : '—'}
						</dd>
						<dd class="text-sm text-muted">conversations</dd>
					</div>
					<div>
						<dt class="text-sm text-muted">Négatif</dt>
						<dd class="figure text-[28px] leading-tight">
							{summary?.totals.total ? formatShare(summary.totals.negative_share) : '—'}
						</dd>
						<dd class="text-sm text-muted">du total</dd>
					</div>
				</dl>

				<div class="flex flex-wrap gap-2 sm:flex-col">
					<a
						href={withQuery(resolve('/(app)'), { veille: watch.id })}
						class="btn btn-primary min-h-11 px-4 text-sm"
					>
						Tableau de bord
					</a>
					<a
						href={withQuery(resolve('/(app)/paroles'), { veille: watch.id })}
						class="btn btn-soft min-h-11 px-4 text-sm"
					>
						Conversations
					</a>
					<a
						href={resolve('/(app)/veilles/[id]', { id: watch.id })}
						class="btn btn-ghost min-h-11 px-4 text-sm"
					>
						Réglages
					</a>
					<button
						type="button"
						class="btn btn-ghost min-h-11 px-4 text-sm"
						disabled={pending === watch.id}
						onclick={() => toggle(watch)}
					>
						{watch.active ? 'Mettre en pause' : 'Reprendre'}
					</button>
				</div>
			</li>
		{:else}
			<li class="card flex flex-col items-start gap-3">
				{#if counts.all === 0}
					<p class="text-lg">Vous n'avez pas encore de veille.</p>
					<a href={resolve('/(app)/veilles/nouvelle')} class="btn btn-primary">Créer ma première veille</a>
				{:else}
					<p class="text-lg">Aucune veille ne correspond.</p>
					<button
						type="button"
						class="btn btn-ghost"
						onclick={() => {
							tab = 'all';
							query = '';
						}}>Voir toutes les veilles</button
					>
				{/if}
			</li>
		{/each}
	</ul>
</div>
