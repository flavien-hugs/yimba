<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Logo, Pagne } from '@yimba/ui';

	const notFound = $derived(page.status === 404);
</script>

<svelte:head>
	<title>{notFound ? 'Page introuvable' : 'Erreur'} · Yimba</title>
</svelte:head>

<header class="bg-white px-4 py-3 sm:px-7">
	<a href={resolve('/(app)')} class="no-underline" aria-label="Yimba, accueil"><Logo /></a>
</header>
<Pagne />
<main class="mx-auto flex max-w-[680px] flex-col gap-5 px-4 py-12">
	<div class="card flex flex-col gap-4 sm:p-10">
		<span class="eyebrow">Erreur {page.status}</span>
		<h1 class="text-3xl leading-tight font-bold tracking-[-0.02em] sm:text-4xl">
			{notFound ? "Cette page n'existe pas" : 'Quelque chose a coincé'}
		</h1>
		<p class="text-lg text-ink-soft">
			{notFound ? "L'adresse est peut-être incomplète, ou la page a été déplacée." : page.error?.message}
		</p>
		<div class="flex flex-wrap gap-2.5">
			<a href={resolve('/(app)')} class="btn btn-primary">Retour à l'accueil</a>
			{#if !notFound}
				<button type="button" class="btn btn-ghost" onclick={() => location.reload()}>Réessayer</button>
			{/if}
		</div>
	</div>
</main>
