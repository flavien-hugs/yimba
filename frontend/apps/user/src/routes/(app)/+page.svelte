<script lang="ts">
	import { resolve } from '$app/paths';
	import { session } from '@yimba/api';
	import {
		Baobab,
		DailyBars,
		EMOTIONS,
		Icon,
		OpinionChart,
		Pagne,
		SOURCES,
		dailySeries,
		firstName,
		formatNumber,
		formatShare,
		formatToday,
		frequencyLabel,
		languageLabel,
		percent,
		plural
	} from '@yimba/ui';
	import type { Emotion, Source } from '@yimba/api';
	import Breakdown from '#lib/Breakdown.svelte';
	import RegionMap from '#lib/RegionMap.svelte';
	import ThemeBars from '#lib/ThemeBars.svelte';
	import MentionCard from '#lib/MentionCard.svelte';
	import { PERIODS, withQuery } from '#lib/watch.js';

	let { data } = $props();

	const user = $derived(session.user ?? data.user);
	const first = $derived(firstName(user.full_name, user.email));

	/** "+18", "−6", "0". */
	const signed = (value: number) => (value > 0 ? `+${value}` : value < 0 ? `−${-value}` : '0');
	const sourceLabel = (key: string) => SOURCES[key as Source] ?? key;

	// Shapes of the small marks of the figures; a little smaller on a phone.
	const SHAPES = {
		circle: 'rounded-full',
		square: 'rounded-[3px] md:rounded-[4px]',
		leaf: 'rounded-[3px_9px_3px_9px] md:rounded-[4px_14px_4px_14px]'
	};

	const view = $derived.by(() => {
		const dashboard = data.dashboard;
		if (!dashboard) return null;
		const { watch, daily, previous, lastDay, days } = dashboard;
		const totals = daily.totals;
		const emotions = Object.entries(daily.emotions)
			.filter((entry): entry is [Emotion, number] => entry[0] in EMOTIONS)
			.sort((a, b) => b[1] - a[1]);
		const expressed = emotions.reduce((sum, [, count]) => sum + count, 0);
		// Compared with the period before only when it had enough conversations to mean something.
		const comparable = previous.total >= 10;
		const growth = comparable ? (totals.total - previous.total) / previous.total : null;
		const kpis = [
			{
				value: formatNumber(totals.total),
				label: 'Conversations',
				note:
					growth === null
						? `sur ${days} jours`
						: `${signed(percent(growth))} % sur les ${days} jours précédents`,
				soft: 'bg-indigo-soft',
				mark: `bg-indigo ${SHAPES.circle}`
			},
			{
				value: totals.total ? formatShare(totals.negative_share) : '—',
				label: 'Ressenti négatif',
				note: [
					comparable
						? `${signed(percent(totals.negative_share) - percent(previous.negative_share))} points`
						: '',
					lastDay.total ? `${formatShare(lastDay.negative_share)} ces dernières 24 h` : ''
				]
					.filter(Boolean)
					.join(', '),
				soft: 'bg-clay-soft',
				mark: `bg-clay ${SHAPES.square}`
			},
			{
				value: emotions.length ? EMOTIONS[emotions[0][0]].label : '—',
				label: 'Ce qui domine',
				note: emotions.length
					? `${formatShare(emotions[0][1] / expressed)} des émotions exprimées`
					: 'Aucune émotion nette',
				soft: 'bg-sun-soft',
				mark: `bg-sun ${SHAPES.leaf}`
			},
			{
				value: formatNumber(dashboard.watchAlerts.length),
				label: dashboard.watchAlerts.length > 1 ? 'Alertes à traiter' : 'Alerte à traiter',
				note: `seuil : ${percent(watch.alert_negative_share)} % de négatif en 24 h`,
				soft: 'bg-leaf-soft',
				mark: `bg-leaf ${SHAPES.circle}`
			}
		];
		const series = dailySeries(daily.buckets, days, dashboard.now);
		const week = series.slice(-7);
		const share = (day: (typeof week)[number]) =>
			formatShare(day.negative / Math.max(1, day.negative + day.neutral + day.positive));
		return {
			...dashboard,
			totals,
			alert: dashboard.watchAlerts.at(0),
			series,
			week,
			weekDescription: `Conversations par jour sur 7 jours : le négatif passe de ${share(week[0])} à ${share(week[week.length - 1])}.`,
			emotions,
			expressed,
			kpis
		};
	});
</script>

<svelte:head>
	<title>Accueil · Yimba</title>
</svelte:head>

{#if !view}
	<section
		class="relative flex flex-wrap items-center gap-6 overflow-hidden rounded-card bg-white px-5 pt-5 pb-8 md:px-8 md:pt-7 md:pb-9"
	>
		<div class="flex min-w-0 flex-[1_1_380px] flex-col gap-3">
			<span class="eyebrow">{formatToday()}</span>
			<h1 class="text-[28px] leading-[1.12] font-bold tracking-[-0.02em] md:text-[40px]">
				Bienvenue {first}, qu'est-ce que vous voulez entendre ?
			</h1>
			<p class="max-w-[56ch] text-ink-soft md:text-lg">
				Une veille suit un sujet : les mots que les gens utilisent pour en parler, les endroits où écouter, et
				le moment où vous prévenir.
			</p>
			<a href={resolve('/(app)/veilles/nouvelle')} class="btn btn-primary mt-1 self-start"
				>Créer ma première veille</a
			>
		</div>
		<Baobab class="w-full max-w-[280px] flex-[0_1_280px]" />
		<Pagne class="absolute inset-x-0 bottom-0" />
	</section>
{:else}
	{@const { watch, totals, alert, series, week, emotions, expressed, kpis, days, now, lastDay } = view}
	{@const conversations = withQuery(resolve('/(app)/paroles'), { veille: watch.id })}

	<div class="flex flex-col gap-3.5 md:gap-5">
		<section
			class="relative flex flex-wrap items-center gap-x-7 gap-y-2.5 overflow-hidden rounded-card bg-white px-5 pt-5 pb-7 md:gap-y-3 md:px-8 md:pt-7 md:pb-9"
		>
			<div class="flex min-w-0 flex-[1_1_380px] flex-col gap-2.5 md:gap-3">
				<span class="eyebrow text-sm md:text-base">{formatToday(now)}</span>
				<h1 class="text-[28px] leading-[1.15] font-bold tracking-[-0.02em] md:text-[40px] md:leading-[1.12]">
					Bonjour {first}, voici ce que disent les gens<span class="hidden md:inline"
						>&nbsp;sur « {watch.name} »</span
					>
				</h1>
				<p class="max-w-[56ch] text-ink-soft md:text-lg">
					{#if !watch.active}
						Cette veille est en pause : Yimba n'écoute plus. Vous pouvez la reprendre depuis ses réglages.
					{:else if totals.total === 0 && lastDay.total === 0}
						Yimba écoute {frequencyLabel(watch.frequency_minutes).toLowerCase()}. Les premières conversations
						apparaîtront ici après la prochaine collecte.
					{:else if lastDay.total === 0}
						Personne n'a pris la parole ces dernières 24 heures. Sur {days} jours : {plural(
							totals.total,
							'conversation'
						)}.
					{:else}
						{plural(lastDay.total, 'conversation')}
						<span class="md:hidden">sur « {watch.name} »</span> ces dernières 24 heures, dont {formatShare(
							lastDay.negative_share
						)} de négatives.{alert ? ' C’est au-dessus du seuil fixé pour cette veille.' : ''}
					{/if}
				</p>
				<div class="mt-1 hidden flex-wrap gap-2.5 md:flex">
					<a href={conversations} class="btn btn-primary">Lire les conversations</a>
					{#if alert}
						<a href={resolve('/(app)/alertes')} class="btn btn-warm">Voir l'alerte</a>
					{/if}
				</div>
			</div>
			<Baobab class="hidden w-full max-w-[280px] flex-[0_1_280px] md:block" />
			<Baobab variant="compact" class="w-full md:hidden" />
			<a href={conversations} class="btn btn-primary w-full md:hidden">Lire les conversations</a>
			<Pagne class="absolute inset-x-0 bottom-0" />
		</section>

		{#if alert}
			<a
				href={resolve('/(app)/alertes')}
				class="flex items-start gap-3 rounded-card bg-sun-soft p-4 no-underline md:hidden"
				aria-label="Alerte en cours : {percent(alert.negative_share)} % de négatif en 24 heures"
			>
				<Icon name="warning" size={26} class="text-sun-deep" />
				<span>
					<span class="block font-bold text-sun-dark"
						>{percent(alert.negative_share)} % de négatif en 24 h</span
					>
					<span class="block text-[15px] text-sun-text">
						Le seuil de la veille est à {percent(alert.threshold_share)} %.
					</span>
				</span>
			</a>
		{/if}

		<nav class="flex rounded-field bg-white p-1 md:hidden" aria-label="Période">
			{#each PERIODS as option (option)}
				<a
					href={withQuery(resolve('/(app)'), { veille: watch.id, periode: option })}
					aria-current={option === days ? 'true' : undefined}
					class="flex min-h-11 flex-1 items-center justify-center rounded-field text-[15px] font-bold no-underline {option ===
					days
						? 'bg-indigo text-white hover:text-white'
						: 'text-ink'}">{option} jours</a
				>
			{/each}
		</nav>

		<section
			class="grid grid-cols-2 gap-2.5 md:grid-cols-[repeat(auto-fit,minmax(220px,1fr))] md:gap-4"
			aria-label="En quelques chiffres"
		>
			{#each kpis as kpi (kpi.label)}
				<div
					class="flex min-w-0 flex-col gap-0.5 rounded-card bg-white p-3.5 md:flex-row md:items-center md:gap-3.5 md:p-5"
				>
					<span
						class="mb-1 flex size-7 shrink-0 items-center justify-center rounded-[6px] md:mb-0 md:size-13 md:rounded-field {kpi.soft}"
					>
						<span class="size-[11px] md:size-4.5 {kpi.mark}"></span>
					</span>
					<div class="flex min-w-0 flex-col">
						<span class="figure text-[28px] leading-[1.1] md:text-[32px]">{kpi.value}</span>
						<span class="text-sm font-bold md:text-base md:font-semibold">{kpi.label}</span>
						<span class="text-[13px] text-muted md:text-sm">{kpi.note}</span>
					</div>
				</div>
			{/each}
		</section>

		<div class="hidden flex-wrap items-stretch gap-4 md:flex">
			<section class="card flex min-w-0 flex-[2_1_520px] flex-col gap-3">
				<div class="flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="text-[22px] font-semibold">Comment l'opinion évolue</h2>
					{@render legend()}
				</div>
				{#if totals.total}
					<OpinionChart
						{series}
						description="Conversations par jour sur {days} jours, réparties en négatif, neutre et positif : {formatShare(
							totals.negative_share
						)} de négatif sur la période."
						marker={alert ? { day: alert.triggered_at.slice(0, 10), label: 'Alerte' } : null}
					/>
					<p class="text-sm text-muted">
						Conversations par jour. Le négatif est tout en bas : on voit sa hausse d'un coup d'œil.
					</p>
				{:else}
					<p class="text-muted">Pas encore de conversation sur cette période.</p>
				{/if}
			</section>

			<section class="card flex min-w-0 flex-[1_1_280px] flex-col gap-3.5">
				<h2 class="text-[22px] font-semibold">Ce que ressentent les gens</h2>
				{#each emotions as [emotion, count] (emotion)}
					<div class="flex flex-col gap-1">
						<div class="flex justify-between tabular-nums">
							<span class="font-bold">{EMOTIONS[emotion].label}</span>
							<span class="text-muted">{formatShare(count / expressed)}</span>
						</div>
						<div class="h-3 overflow-hidden rounded-[6px] bg-track">
							<div
								class="h-3 rounded-[6px] {EMOTIONS[emotion].bar}"
								style:width="{(count / emotions[0][1]) * 100}%"
							></div>
						</div>
					</div>
				{:else}
					<p class="text-muted">Pas encore assez de conversations pour dégager une émotion.</p>
				{/each}
				{#if expressed && totals.total}
					<p class="text-sm text-muted">
						Calculé sur les {formatShare(expressed / totals.total)} de conversations où une émotion se détache.
					</p>
				{/if}
			</section>
		</div>

		<div class="hidden flex-wrap items-stretch gap-4 md:flex">
			<RegionMap places={view.places} />
			<ThemeBars themes={view.themes} />
		</div>

		<section class="flex flex-col gap-2.5 rounded-card bg-white p-4.5 md:hidden">
			<h2 class="text-xl font-semibold">Les 7 derniers jours</h2>
			<DailyBars series={week} description={view.weekDescription} />
			{@render legend()}
		</section>

		<div class="hidden flex-wrap items-stretch gap-4 md:flex">
			<Breakdown
				title="Où on en parle"
				description="Conversations par source, avec leur part de négatif."
				buckets={view.bySource}
				label={sourceLabel}
			/>
			<Breakdown
				title="Dans quelle langue"
				description="Le nouchi est reconnu à part du français."
				buckets={view.byLanguage}
				label={languageLabel}
			/>
		</div>

		<ThemeBars themes={view.themes} compact class="md:hidden" />

		<section class="flex flex-col gap-2.5 md:gap-3" aria-labelledby="voices">
			<div class="flex flex-wrap items-baseline justify-between gap-2">
				<h2 id="voices" class="mt-1 text-xl font-semibold md:mt-0 md:text-[22px]">Les voix du moment</h2>
				<a href={conversations} class="hidden font-bold md:inline">Toutes les conversations</a>
			</div>
			{#if view.voices.length}
				<div class="grid gap-2.5 md:grid-cols-[repeat(auto-fit,minmax(260px,1fr))] md:gap-4">
					{#each view.voices as mention, index (mention.id)}
						<!-- Two voices on a phone, three on a wider screen. -->
						<div class={index > 1 ? 'hidden md:block' : ''}>
							<MentionCard {mention} variant="voice" class="h-full" />
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-muted">Aucune conversation pour l'instant.</p>
			{/if}
		</section>
	</div>
{/if}

{#snippet legend()}
	<div
		class="flex flex-wrap gap-x-3.5 gap-y-1 text-[13px] text-muted md:gap-x-4 md:text-sm"
		aria-hidden="true"
	>
		<span class="inline-flex items-center gap-1.5"><span class="size-3 rounded bg-clay"></span>Négatif</span>
		<span class="inline-flex items-center gap-1.5"><span class="size-3 rounded bg-sand"></span>Neutre</span>
		<span class="inline-flex items-center gap-1.5"><span class="size-3 rounded bg-leaf"></span>Positif</span>
	</div>
{/snippet}
