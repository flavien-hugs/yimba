<!-- Creates a watch, or changes one: what to listen to, where, and when to raise an alert. -->
<script lang="ts">
	import { untrack } from 'svelte';
	import { goto, invalidate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, describe, type Source, type Watch, type WatchCreate } from '@yimba/api';
	import {
		FREQUENCIES,
		Icon,
		Notice,
		Pagne,
		SearchSelect,
		SOURCES,
		SOURCE_ORDER,
		frequencyLabel,
		languageLabel
	} from '@yimba/ui';
	import { withQuery } from './watch.js';

	let { watch = null }: { watch?: Watch | null } = $props();

	const MAX_KEYWORDS = 20;
	const SOURCE_PHRASES: Record<Source, string> = {
		facebook: 'Facebook',
		instagram: 'Instagram',
		youtube: 'YouTube',
		bluesky: 'Bluesky',
		news: 'la presse en ligne',
		gdelt: 'la presse internationale'
	};
	const listOf = new Intl.ListFormat('fr', { style: 'long', type: 'conjunction' });

	// The form starts from the watch it edits; the page recreates it when the watch changes.
	const initial = untrack(() => $state.snapshot(watch));
	const LANGUAGES = [
		{ value: 'fr', label: 'Français, nouchi compris', phrase: 'en français, nouchi compris' },
		{ value: 'fr,en', label: 'Français et anglais', phrase: 'en français et en anglais' }
	];
	const initialLanguages = (initial?.languages ?? ['fr']).join(',');
	if (!LANGUAGES.some((choice) => choice.value === initialLanguages)) {
		const names = listOf.format(initialLanguages.split(',').map((code) => languageLabel(code).toLowerCase()));
		LANGUAGES.push({ value: initialLanguages, label: names, phrase: `en ${names}` });
	}
	const COUNTRIES = [{ value: 'CI', label: "Côte d'Ivoire" }];
	const initialCountries = (initial?.countries ?? ['CI']).join(',');
	if (!COUNTRIES.some((choice) => choice.value === initialCountries)) {
		COUNTRIES.push({ value: initialCountries, label: initialCountries.replaceAll(',', ', ') });
	}

	let name = $state(initial?.name ?? '');
	let keywords = $state<string[]>(initial?.keywords ?? []);
	let draft = $state('');
	let sources = $state<Source[]>(initial?.sources ?? ['facebook', 'news']);
	let languages = $state(initialLanguages);
	let countries = $state(initialCountries);
	let frequency = $state(initial?.frequency_minutes ?? 60);
	let threshold = $state(Math.round((initial?.alert_negative_share ?? 0.4) * 100));
	let minimum = $state(initial?.alert_min_mentions ?? 20);

	let step = $state(1);
	let busy = $state(false);
	let error = $state('');
	let saved = $state(false);
	let confirmingDelete = $state(false);

	const STEPS = ['Le sujet', 'Où écouter', 'Quand vous prévenir'];
	// A new watch is filled in step by step; an existing one can be saved from any step.
	const last = $derived(step === 3 || watch !== null);

	/** What is wrong in a step, as sentences; empty when it can be left. */
	function problemsOf(which: number): string[] {
		const found =
			which === 1
				? [!name.trim() && 'Donnez un nom à la veille.', !keywords.length && 'Ajoutez au moins un mot.']
				: which === 2
					? [!sources.length && 'Choisissez au moins une source.']
					: [
							!(threshold >= 1 && threshold <= 100) && 'Le seuil doit être compris entre 1 et 100 %.',
							!(minimum >= 1) && 'Il faut au moins 1 conversation pour déclencher une alerte.'
						];
		return found.filter((problem): problem is string => typeof problem === 'string');
	}

	function next() {
		if (draft.trim()) addKeywords(draft);
		const problems = problemsOf(step);
		error = problems.join(' ');
		if (!problems.length) step += 1;
	}

	function addKeywords(text: string) {
		for (const part of text.split(',')) {
			const word = part.trim().replace(/\s+/g, ' ').slice(0, 100);
			const known = keywords.some((keyword) => keyword.toLowerCase() === word.toLowerCase());
			if (word && !known && keywords.length < MAX_KEYWORDS) keywords.push(word);
		}
		draft = '';
	}

	function onKeywordKey(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ',') {
			event.preventDefault();
			addKeywords(draft);
		} else if (event.key === 'Backspace' && !draft && keywords.length) {
			keywords.pop();
		}
	}

	const listen = $derived.by(() => {
		const where = SOURCE_ORDER.filter((source) => sources.includes(source)).map(
			(source) => SOURCE_PHRASES[source]
		);
		if (!keywords.length || !where.length) {
			return 'Ajoutez au moins un mot et une source : Yimba saura quoi écouter, et où.';
		}
		const words = listOf.format(keywords.map((keyword) => `« ${keyword} »`));
		const language = LANGUAGES.find((choice) => choice.value === languages)?.phrase ?? '';
		return `${frequencyLabel(frequency)}, écouter ${words} sur ${listOf.format(where)}, ${language}.`;
	});

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		// Enter in a field of an early step goes to the next step instead of launching the watch.
		if (!last) return next();
		if (draft.trim()) addKeywords(draft);
		// Each problem sends back to the step concerned.
		for (const which of [1, 2, 3]) {
			const problems = problemsOf(which);
			if (problems.length) {
				step = which;
				error = problems.join(' ');
				return;
			}
		}

		const body: WatchCreate = {
			name: name.trim(),
			keywords: $state.snapshot(keywords),
			sources: $state.snapshot(sources),
			languages: languages.split(','),
			countries: countries.split(','),
			frequency_minutes: frequency,
			alert_negative_share: threshold / 100,
			alert_min_mentions: minimum
		};
		busy = true;
		error = '';
		saved = false;
		try {
			if (watch) {
				await api.watches.update(watch.id, body);
				await invalidate('yimba:watches');
				saved = true;
			} else {
				const created = await api.watches.create(body);
				await goto(withQuery(resolve('/(app)'), { veille: created.id }), { refreshAll: true });
			}
		} catch (caught) {
			error = describe(caught);
		} finally {
			busy = false;
		}
	}

	async function toggleActive() {
		if (!watch) return;
		busy = true;
		error = '';
		try {
			await api.watches.update(watch.id, { active: !watch.active });
			await invalidate('yimba:watches');
		} catch (caught) {
			error = describe(caught);
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (!watch) return;
		busy = true;
		error = '';
		try {
			await api.watches.remove(watch.id);
			await goto(resolve('/(app)'), { refreshAll: true });
		} catch (caught) {
			error = describe(caught);
			busy = false;
		}
	}
</script>

<div class="flex w-full max-w-[1120px] flex-col gap-6">
	<div class="flex flex-col gap-2.5">
		<span class="eyebrow">{watch ? 'Réglages de la veille' : 'Créer une veille'}</span>
		<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-[40px]">
			{watch ? watch.name : "Qu'est-ce que vous voulez entendre ?"}
		</h1>
		<p class="max-w-[60ch] text-lg text-ink-soft">
			Choisissez un sujet et les mots que les gens utilisent pour en parler. Yimba écoute, comprend et vous
			prévient quand l'opinion se tend.
		</p>
	</div>

	<div class="flex flex-wrap gap-2.5" role="group" aria-label="Étapes">
		{#each STEPS as label, index (label)}
			{@const active = step === index + 1}
			<button
				type="button"
				class="inline-flex min-h-11 cursor-pointer items-center gap-2.5 rounded-field py-0 pr-4 pl-2 font-bold {active
					? 'bg-indigo text-white'
					: 'bg-white text-ink hover:bg-haze'}"
				aria-current={active ? 'step' : undefined}
				onclick={() => (step = index + 1)}
			>
				<span
					class="flex size-7.5 items-center justify-center rounded-full font-display text-[15px] font-bold {active
						? 'bg-sun text-ink'
						: 'bg-indigo-soft text-indigo-deep'}">{index + 1}</span
				>{label}
			</button>
		{/each}
	</div>

	<div class="flex flex-wrap items-start gap-5">
		<form id="watch-form" class="flex min-w-0 flex-[2_1_520px] flex-col gap-4" onsubmit={submit} novalidate>
			<section class="card flex flex-col gap-4 sm:p-6.5" hidden={step !== 1}>
				<h2 class="text-2xl font-semibold">1. Le sujet</h2>
				<label class="label">
					Comment voulez-vous l'appeler ?
					<input class="field" type="text" maxlength="200" required bind:value={name} />
				</label>
				<div class="flex flex-col gap-1.5">
					<label for="keywords" class="font-bold">
						Quels mots les gens utilisent-ils ?
						<span class="font-normal text-muted"
							>Tapez un mot puis validez. Pensez aux façons de parler du quotidien.</span
						>
					</label>
					<div
						class="flex flex-wrap items-center gap-2 rounded-field border-[1.5px] border-line bg-white px-2.5 py-2 focus-within:border-indigo"
					>
						{#each keywords as keyword, index (keyword)}
							<span
								class="inline-flex min-h-9.5 items-center gap-1.5 rounded-field bg-indigo-soft py-0 pr-1.5 pl-3.5 font-bold text-indigo-deep"
							>
								{keyword}
								<button
									type="button"
									class="flex size-7.5 items-center justify-center rounded-full text-lg hover:bg-indigo-mist"
									aria-label="Retirer {keyword}"
									onclick={() => keywords.splice(index, 1)}><Icon name="close" size={14} /></button
								>
							</span>
						{/each}
						<input
							id="keywords"
							type="text"
							placeholder={keywords.length < MAX_KEYWORDS ? 'Ajouter un mot' : '20 mots au plus'}
							disabled={keywords.length >= MAX_KEYWORDS}
							class="min-h-9.5 min-w-0 flex-[1_1_160px] bg-transparent text-[17px] outline-none"
							bind:value={draft}
							onkeydown={onKeywordKey}
							onblur={() => draft.trim() && addKeywords(draft)}
						/>
					</div>
				</div>
				<div class="flex flex-wrap justify-between gap-2.5 pt-2">
					<span></span>
					<button type="button" class="btn btn-soft" onclick={next}>Suivant</button>
				</div>
			</section>

			<section class="card flex flex-col gap-4 sm:p-6.5" hidden={step !== 2}>
				<h2 class="text-2xl font-semibold">2. Où écouter</h2>
				<fieldset class="flex flex-col gap-2">
					<legend class="sr-only">Sources</legend>
					<div class="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-2.5">
						{#each SOURCE_ORDER as source (source)}
							{@const checked = sources.includes(source)}
							<label
								class="flex min-h-14 items-center gap-3 rounded-field border-2 px-4 font-bold {checked
									? 'border-indigo bg-indigo-wash'
									: 'border-line-strong bg-white'}"
							>
								<input type="checkbox" class="size-5.5 accent-indigo" value={source} bind:group={sources} />
								{SOURCES[source]}
							</label>
						{/each}
					</div>
				</fieldset>
				<div class="grid gap-4 sm:grid-cols-2">
					<div class="label justify-between">
						<label for="languages">Langues</label>
						<SearchSelect
							id="languages"
							options={LANGUAGES.map(({ value, label }) => ({ value, label }))}
							bind:value={languages}
						/>
					</div>
					<div class="label justify-between">
						<label for="countries">Pays</label>
						<SearchSelect id="countries" options={COUNTRIES} bind:value={countries} />
					</div>
				</div>
				<div class="flex flex-wrap justify-between gap-2.5 pt-2">
					<button type="button" class="btn btn-ghost" onclick={() => (step = 1)}>Précédent</button>
					<button type="button" class="btn btn-soft" onclick={next}>Suivant</button>
				</div>
			</section>

			<section class="card flex flex-col gap-4 sm:p-6.5" hidden={step !== 3}>
				<h2 class="text-2xl font-semibold">3. Quand vous prévenir</h2>
				<fieldset class="flex flex-col gap-2">
					<legend class="mb-2 font-bold">À quelle fréquence Yimba doit-il écouter ?</legend>
					<div class="flex flex-wrap gap-2">
						{#each FREQUENCIES as option (option.minutes)}
							<label
								class="inline-flex min-h-12 items-center gap-2.5 rounded-field border-2 px-4.5 font-bold {frequency ===
								option.minutes
									? 'border-indigo bg-indigo-wash'
									: 'border-line-strong bg-white'}"
							>
								<input
									type="radio"
									name="frequency"
									class="size-5 accent-indigo"
									value={option.minutes}
									bind:group={frequency}
								/>
								{option.label}
							</label>
						{/each}
					</div>
				</fieldset>
				<div class="grid gap-4 sm:grid-cols-2">
					<label class="label justify-between">
						Me prévenir si le négatif dépasse (%)
						<input class="field" type="number" min="1" max="100" required bind:value={threshold} />
					</label>
					<label class="label justify-between">
						à partir de combien de conversations (24 h) ?
						<input class="field" type="number" min="1" required bind:value={minimum} />
					</label>
				</div>
				<p class="max-w-[66ch] text-muted">
					Un minimum évite les fausses alertes : 3 conversations négatives sur 4 ne disent rien de l'opinion
					d'un pays.
				</p>
				<div class="flex flex-wrap justify-between gap-2.5 pt-2">
					<button type="button" class="btn btn-ghost" onclick={() => (step = 2)}>Précédent</button>
				</div>
			</section>

			{#if watch}
				<section class="card flex flex-col gap-4 sm:p-6.5" hidden={step !== 1}>
					<h2 class="text-2xl font-semibold">La veille</h2>
					<p class="text-ink-soft">
						{watch.active
							? 'Yimba écoute ce sujet. En pause, il arrête de collecter ; les conversations déjà reçues restent.'
							: 'Cette veille est en pause : Yimba ne collecte plus rien pour elle.'}
					</p>
					<div class="flex flex-wrap gap-2.5">
						<button type="button" class="btn btn-ghost" disabled={busy} onclick={toggleActive}>
							{watch.active ? 'Mettre en pause' : 'Reprendre la veille'}
						</button>
						{#if !confirmingDelete}
							<button type="button" class="btn btn-ghost text-clay" onclick={() => (confirmingDelete = true)}>
								Supprimer la veille
							</button>
						{/if}
					</div>
					{#if confirmingDelete}
						<div class="flex flex-col gap-3 rounded-field bg-clay-soft p-4 text-clay-ink" role="alert">
							<p>
								Supprimer « {watch.name} » ? Ses conversations et ses alertes ne seront plus visibles. Cette action
								ne peut pas être annulée.
							</p>
							<div class="flex flex-wrap gap-2.5">
								<button type="button" class="btn btn-danger" disabled={busy} onclick={remove}
									>Supprimer</button
								>
								<button type="button" class="btn btn-ghost" onclick={() => (confirmingDelete = false)}
									>Annuler</button
								>
							</div>
						</div>
					{/if}
				</section>
			{/if}
		</form>

		<aside
			class="relative flex min-w-0 flex-[1_1_300px] flex-col gap-3.5 overflow-hidden rounded-card bg-indigo px-6.5 pt-6.5 pb-9 text-white lg:sticky lg:top-24"
			aria-label="Résumé de la veille"
		>
			<span class="font-bold text-sun">Ce que Yimba va faire pour vous</span>
			<p class="font-display text-2xl leading-[1.3] font-medium" aria-live="polite">{listen}</p>
			<p class="text-indigo-mist">
				Chaque conversation est comprise : langue, ressenti, émotion. Les personnes restent anonymes.
			</p>
			<p class="text-indigo-mist">
				Vous serez prévenu·e si {threshold} % ou plus des conversations des dernières 24 heures sont négatives,
				à partir de
				{minimum} conversations.
			</p>
			{#if error}
				<Notice tone="danger">{error}</Notice>
			{/if}
			{#if saved}
				<Notice tone="success">Modifications enregistrées.</Notice>
			{/if}
			<div class="mt-1.5 flex flex-col gap-2.5">
				<button type="submit" form="watch-form" class="btn btn-sun min-h-13.5 text-[17px]" disabled={busy}>
					{busy ? 'Un instant…' : !last ? 'Continuer' : watch ? 'Enregistrer' : 'Lancer la veille'}
				</button>
				<a
					href={watch ? withQuery(resolve('/(app)'), { veille: watch.id }) : resolve('/(app)')}
					class="flex min-h-11.5 items-center justify-center font-bold text-white hover:text-sun"
				>
					{watch ? 'Retour au tableau de bord' : 'Plus tard'}
				</a>
			</div>
			<Pagne class="absolute inset-x-0 bottom-0" />
		</aside>
	</div>
</div>
