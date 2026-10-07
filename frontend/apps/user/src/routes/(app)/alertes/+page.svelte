<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, describe, type Alert } from '@yimba/api';
	import { Notice, formatMoment, formatNumber, percent, plural } from '@yimba/ui';
	import { withQuery } from '#lib/watch.js';

	let { data } = $props();

	const open = $derived(data.alerts.filter((alert) => alert.status === 'open'));
	const handled = $derived(data.alerts.filter((alert) => alert.status !== 'open'));
	const shown = $derived(data.handled ? handled : open);

	let pending = $state<string | null>(null);
	let error = $state('');

	async function acknowledge(alert: Alert) {
		pending = alert.id;
		error = '';
		try {
			await api.watches.acknowledge(alert.watch_id, alert.id);
			await invalidate('yimba:alerts');
		} catch (caught) {
			error = describe(caught);
		} finally {
			pending = null;
		}
	}

	/** Clearly above the threshold: clay; just above it: sun. */
	const tone = (alert: Alert) =>
		alert.negative_share - alert.threshold_share >= 0.05
			? 'bg-clay-soft text-clay-ink'
			: 'bg-sun-soft text-sun-ink';
	const hours = (alert: Alert) =>
		Math.round((Date.parse(alert.window_end) - Date.parse(alert.window_start)) / 3_600_000);
</script>

<svelte:head>
	<title>Alertes · Yimba</title>
</svelte:head>

<div class="flex flex-col gap-4.5">
	<header class="flex flex-col gap-1.5">
		<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">Alertes</h1>
		<p class="max-w-[66ch] text-[17px] text-muted">
			Yimba vous prévient quand la part de paroles négatives dépasse le seuil fixé pour une veille, sur les
			dernières 24 heures. Il attend assez de conversations pour que le chiffre soit fiable, et ne vous
			relance pas avant 6 heures.
		</p>
	</header>

	<nav class="flex flex-wrap gap-2" aria-label="État des alertes">
		<a
			href={withQuery(resolve('/(app)/alertes'), { veille: data.filter })}
			class="tab"
			aria-current={data.handled ? undefined : 'true'}
		>
			À traiter · {formatNumber(open.length)}
		</a>
		<a
			href={withQuery(resolve('/(app)/alertes'), { veille: data.filter, etat: 'traitees' })}
			class="tab"
			aria-current={data.handled ? 'true' : undefined}
		>
			Traitées · {formatNumber(handled.length)}
		</a>
	</nav>

	{#if error}
		<Notice tone="danger">{error}</Notice>
	{/if}

	<section class="flex flex-col gap-3.5" aria-label={data.handled ? 'Alertes traitées' : 'Alertes à traiter'}>
		{#each shown as alert (alert.id)}
			<article class="flex flex-wrap items-center gap-x-7 gap-y-4 rounded-card bg-white px-6 py-5.5">
				<div
					class="flex size-26 shrink-0 flex-col items-center justify-center rounded-full sm:size-33 {tone(
						alert
					)}"
					aria-hidden="true"
				>
					<span class="figure text-3xl leading-none sm:text-[40px]">{percent(alert.negative_share)} %</span>
					<span class="text-[13px] text-ink-soft">négatif</span>
				</div>
				<div class="flex min-w-0 flex-[1_1_320px] flex-col gap-1.5">
					<div class="flex flex-wrap items-center gap-2.5">
						<h2 class="text-[22px] font-semibold">{data.watchNames[alert.watch_id] ?? 'Veille supprimée'}</h2>
						{#if alert.status === 'open'}
							<span class="tag bg-sun-soft text-sun-ink">À traiter</span>
						{:else}
							<span class="tag bg-leaf-soft text-leaf-ink">Traitée</span>
						{/if}
					</div>
					<p class="text-[17px]">
						<span class="sr-only">{percent(alert.negative_share)} % de négatif : </span>
						{plural(alert.mentions, 'conversation')} en {hours(alert)} h, dont {plural(
							alert.negative,
							'négative'
						)}.
					</p>
					<p class="text-sm text-muted">
						Déclenchée {formatMoment(alert.triggered_at)} · seuil de la veille : {percent(
							alert.threshold_share
						)} %
						{#if alert.acknowledged_at}· traitée {formatMoment(alert.acknowledged_at)}{/if}
					</p>
				</div>
				<div class="flex shrink-0 flex-col gap-2">
					<a
						href={withQuery(resolve('/(app)/paroles'), {
							veille: alert.watch_id,
							ressenti: 'negative',
							debut: alert.window_start,
							fin: alert.window_end
						})}
						class="btn btn-primary"
					>
						Lire les conversations
					</a>
					{#if alert.status === 'open'}
						<button
							type="button"
							class="btn btn-ghost text-indigo"
							disabled={pending === alert.id}
							onclick={() => acknowledge(alert)}
						>
							{pending === alert.id ? 'Un instant…' : "C'est traité"}
						</button>
					{/if}
				</div>
			</article>
		{:else}
			<div class="card">
				<p class="text-lg">
					{data.handled
						? "Aucune alerte traitée pour l'instant."
						: "Rien à traiter. Yimba vous prévient ici dès qu'une veille dépasse son seuil."}
				</p>
			</div>
		{/each}
	</section>
</div>
