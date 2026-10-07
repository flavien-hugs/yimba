<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, describe, type Alert } from '@yimba/api';
	import {
		Icon,
		Notice,
		formatClock,
		formatDate,
		formatMoment,
		formatNumber,
		percent,
		plural
	} from '@yimba/ui';
	import { withQuery } from '#lib/watch.js';

	let { data } = $props();

	const TABS = [
		{ value: null, label: 'À traiter', count: () => data.counts.open },
		{ value: 'traitees', label: 'Traitées', count: () => data.counts.handled },
		{ value: 'toutes', label: 'Toutes', count: () => data.counts.all }
	] as const;

	let pending = $state<string | null>(null);
	let confirming = $state(false);
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

	async function acknowledge(alerts: { id: string; watch_id: string }[]) {
		pending = alerts.length === 1 ? alerts[0].id : '*';
		error = '';
		try {
			await Promise.all(alerts.map((alert) => api.watches.acknowledge(alert.watch_id, alert.id)));
			await invalidate('yimba:alerts');
		} catch (caught) {
			error = describe(caught);
		} finally {
			pending = null;
			confirming = false;
		}
	}

	// The alerts of the page, grouped by day: "Aujourd'hui", "Hier", "3 octobre".
	const days = $derived.by(() => {
		const groups: { key: string; label: string; alerts: Alert[] }[] = [];
		const today = new Date().toDateString();
		const yesterday = new Date(Date.now() - 86_400_000).toDateString();
		for (const alert of data.alerts) {
			const moment = new Date(alert.triggered_at);
			const key = moment.toDateString();
			const label = key === today ? "Aujourd'hui" : key === yesterday ? 'Hier' : formatDate(moment);
			const last = groups.at(-1);
			if (last?.key === key) last.alerts.push(alert);
			else groups.push({ key, label, alerts: [alert] });
		}
		return groups;
	});

	const hours = (alert: Alert) =>
		Math.round((Date.parse(alert.window_end) - Date.parse(alert.window_start)) / 3_600_000);
	/** Clearly above the threshold: clay; just above it: sun. */
	const severe = (alert: Alert) => alert.negative_share - alert.threshold_share >= 0.05;

	const first = $derived((data.pageNumber - 1) * data.pageSize + 1);
	const last = $derived(first + data.alerts.length - 1);
	const numbers = $derived.by(() => {
		const wanted = new Set([1, data.pages, ...[-2, -1, 0, 1, 2].map((shift) => data.pageNumber + shift)]);
		const sorted = [...wanted].filter((n) => n >= 1 && n <= data.pages).sort((a, b) => a - b);
		return sorted.flatMap((n, index) => (index && n - sorted[index - 1] > 1 ? [0, n] : [n]));
	});
</script>

<svelte:head>
	<title>Alertes · Yimba</title>
</svelte:head>

<div class="flex flex-col gap-5">
	<header class="flex flex-col gap-1.5">
		<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">Alertes</h1>
		<p class="max-w-[66ch] text-[17px] text-muted">
			Yimba vous prévient quand la part de paroles négatives dépasse le seuil fixé pour une veille, sur les
			dernières 24 heures. Il attend assez de conversations pour que le chiffre soit fiable, et ne vous
			relance pas avant 6 heures.
		</p>
	</header>

	<dl class="grid gap-3 sm:grid-cols-3">
		<div class="flex items-center gap-3.5 rounded-card bg-white p-4.5">
			<span class="flex size-11 shrink-0 items-center justify-center rounded-field bg-sun-soft text-sun-deep">
				<Icon name="bell" />
			</span>
			<div class="flex flex-col leading-tight">
				<dd class="figure text-[28px]">{formatNumber(data.counts.open)}</dd>
				<dt class="text-sm text-muted">{data.counts.open > 1 ? 'alertes à traiter' : 'alerte à traiter'}</dt>
			</div>
		</div>
		<div class="flex items-center gap-3.5 rounded-card bg-white p-4.5">
			<span
				class="flex size-11 shrink-0 items-center justify-center rounded-field bg-leaf-soft text-leaf-ink"
			>
				<Icon name="check" />
			</span>
			<div class="flex flex-col leading-tight">
				<dd class="figure text-[28px]">{formatNumber(data.counts.handled)}</dd>
				<dt class="text-sm text-muted">{data.counts.handled > 1 ? 'alertes traitées' : 'alerte traitée'}</dt>
			</div>
		</div>
		<div class="flex items-center gap-3.5 rounded-card bg-white p-4.5">
			<span
				class="flex size-11 shrink-0 items-center justify-center rounded-field bg-indigo-soft text-indigo-deep"
			>
				<Icon name="calendar" />
			</span>
			<div class="flex min-w-0 flex-col leading-tight">
				<dd class="truncate text-lg font-bold">{data.latest ? formatMoment(data.latest) : '—'}</dd>
				<dt class="text-sm text-muted">dernière alerte</dt>
			</div>
		</div>
	</dl>

	<div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
		<nav class="flex flex-wrap gap-2" aria-label="État des alertes">
			{#each TABS as tab (tab.label)}
				<a
					href={changed({ etat: tab.value, page: null })}
					class="tab"
					aria-current={(data.state === 'ouvertes' ? null : data.state) === tab.value ? 'true' : undefined}
				>
					{tab.label} · {formatNumber(tab.count())}
				</a>
			{/each}
		</nav>
		<div class="flex flex-wrap items-center gap-2">
			<a
				href={changed({ ordre: data.ascending ? null : 'asc', page: null })}
				class="flex min-h-11.5 items-center gap-2 rounded-field bg-white px-3.5 text-sm font-bold text-ink no-underline hover:text-indigo"
				title="Inverser l'ordre"
				aria-label="{data.ascending ? 'Plus anciennes d’abord' : 'Plus récentes d’abord'} : inverser l'ordre"
			>
				<Icon name={data.ascending ? 'sort-asc' : 'sort-desc'} size={18} />
				{data.ascending ? 'Plus anciennes d’abord' : 'Plus récentes d’abord'}
			</a>
			{#if data.state === 'ouvertes' && data.counts.open > 1}
				{#if confirming}
					<span
						class="flex flex-wrap items-center gap-2 rounded-field bg-sun-soft py-1 pr-1 pl-3.5 text-sm text-sun-text"
						role="alert"
					>
						Marquer {plural(data.counts.open, 'alerte')} comme traitées ?
						<button
							type="button"
							class="btn btn-primary min-h-10 px-3.5 text-sm"
							disabled={pending === '*'}
							onclick={() => acknowledge(data.open)}>Confirmer</button
						>
						<button
							type="button"
							class="btn btn-ghost min-h-10 px-3.5 text-sm"
							onclick={() => (confirming = false)}>Annuler</button
						>
					</span>
				{:else}
					<button
						type="button"
						class="btn btn-ghost min-h-11.5 px-4 text-sm"
						onclick={() => (confirming = true)}
					>
						<Icon name="check" size={18} /> Tout marquer comme traité
					</button>
				{/if}
			{/if}
		</div>
	</div>

	{#if error}
		<Notice tone="danger">{error}</Notice>
	{/if}

	{#if data.alerts.length}
		<div class="overflow-hidden rounded-card bg-white">
			{#each days as day (day.key)}
				<section aria-label={day.label}>
					<h2
						class="border-b border-rule bg-lilac px-5.5 py-2 text-sm font-bold text-muted not-first:border-t"
					>
						{day.label}
					</h2>
					<ul class="divide-y divide-rule">
						{#each day.alerts as alert (alert.id)}
							{@const isOpen = alert.status === 'open'}
							<li
								class="grid gap-x-5 gap-y-3 px-5.5 py-4.5 md:grid-cols-[88px_minmax(0,1fr)_auto] md:items-center"
							>
								<div class="flex items-baseline gap-2 md:flex-col md:items-start md:gap-0">
									<span
										class="figure text-[30px] leading-none {severe(alert) ? 'text-clay-ink' : 'text-sun-ink'}"
									>
										{percent(alert.negative_share)} %
									</span>
									<span class="text-[13px] text-muted">négatif</span>
								</div>

								<div class="flex min-w-0 flex-col gap-1.5">
									<div class="flex flex-wrap items-center gap-x-2.5 gap-y-1">
										<a
											href={withQuery(resolve('/(app)'), { veille: alert.watch_id })}
											class="min-w-0 truncate text-lg font-semibold text-ink no-underline hover:text-indigo"
											>{data.watchNames[alert.watch_id] ?? 'Veille supprimée'}</a
										>
										<span class="tag {isOpen ? 'bg-sun-soft text-sun-ink' : 'bg-leaf-soft text-leaf-ink'}">
											{isOpen ? 'À traiter' : 'Traitée'}
										</span>
										<span class="text-sm text-muted">{formatClock(alert.triggered_at)}</span>
									</div>
									<p class="text-[15px]">
										{plural(alert.negative, 'négative')} sur {plural(alert.mentions, 'conversation')}, en {hours(
											alert
										)} h
										{#if alert.acknowledged_at}
											<span class="text-muted">· traitée {formatMoment(alert.acknowledged_at)}</span>
										{/if}
									</p>
									<div class="flex items-center gap-3">
										<div class="relative h-2 max-w-72 flex-1 rounded-[4px] bg-track" aria-hidden="true">
											<div
												class="h-full rounded-[4px] {severe(alert) ? 'bg-clay' : 'bg-gold'}"
												style:width="{Math.min(100, alert.negative_share * 100)}%"
											></div>
											<div
												class="absolute -top-1 h-4 w-0.5 rounded bg-ink"
												style:left="{Math.min(100, alert.threshold_share * 100)}%"
											></div>
										</div>
										<span class="text-[13px] whitespace-nowrap text-muted"
											>seuil {percent(alert.threshold_share)} %</span
										>
									</div>
								</div>

								<div class="flex flex-wrap gap-2 md:justify-end">
									<a
										href={withQuery(resolve('/(app)/paroles'), {
											veille: alert.watch_id,
											ressenti: 'negative',
											debut: alert.window_start,
											fin: alert.window_end
										})}
										class="btn btn-soft min-h-11 px-4 text-sm"
									>
										Lire les conversations
									</a>
									{#if isOpen}
										<button
											type="button"
											class="btn btn-ghost min-h-11 px-4 text-sm"
											disabled={pending === alert.id || pending === '*'}
											onclick={() => acknowledge([alert])}
										>
											<Icon name="check" size={18} />
											{pending === alert.id ? 'Un instant…' : "C'est traité"}
										</button>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>

		{#if data.pages > 1}
			<nav class="flex flex-wrap items-center justify-between gap-3" aria-label="Pages d'alertes">
				<p class="text-sm text-muted tabular-nums" aria-live="polite">
					Alertes {formatNumber(first)} à {formatNumber(last)} sur {formatNumber(data.total)}
				</p>
				<ul class="flex flex-wrap items-center gap-1.5">
					<li>
						{#if data.pageNumber > 1}
							<a
								href={changed({ page: String(data.pageNumber - 1) })}
								class="btn btn-ghost min-h-11 px-4 text-sm">Précédente</a
							>
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
									aria-current={number === data.pageNumber ? 'page' : undefined}
									aria-label="Page {number}">{number}</a
								>
							{/if}
						</li>
					{/each}
					<li>
						{#if data.pageNumber < data.pages}
							<a
								href={changed({ page: String(data.pageNumber + 1) })}
								class="btn btn-ghost min-h-11 px-4 text-sm">Suivante</a
							>
						{:else}
							<span class="btn btn-ghost min-h-11 px-4 text-sm" aria-disabled="true">Suivante</span>
						{/if}
					</li>
				</ul>
			</nav>
		{/if}
	{:else}
		<div class="card flex flex-col items-start gap-3">
			<p class="text-lg">
				{data.state === 'traitees'
					? "Aucune alerte traitée pour l'instant."
					: data.state === 'toutes'
						? "Aucune alerte pour l'instant."
						: "Rien à traiter. Yimba vous prévient ici dès qu'une veille dépasse son seuil."}
			</p>
			{#if data.state !== 'toutes' && data.counts.all > 0}
				<a href={changed({ etat: 'toutes', page: null })} class="btn btn-ghost">Voir toutes les alertes</a>
			{/if}
		</div>
	{/if}
</div>
