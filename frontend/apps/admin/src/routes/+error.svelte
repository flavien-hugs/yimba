<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { session } from '@yimba/api';
	import { Logo, Pagne } from '@yimba/ui';

	// Where the user app is: the same site by default, another address when it has an image of its own.
	const USER_URL: string = import.meta.env.VITE_USER_URL || '/';

	const forbidden = $derived(page.status === 403);
	const notFound = $derived(page.status === 404);

	async function logout() {
		await session.logout();
		await goto(resolve('/connexion'));
	}
</script>

<svelte:head>
	<title>Erreur · Administration Yimba</title>
</svelte:head>

<header class="bg-white px-4 py-3 sm:px-7">
	<Logo />
</header>
<Pagne />
<main class="mx-auto flex max-w-[680px] flex-col gap-5 px-4 py-12">
	<div class="card flex flex-col gap-4 sm:p-10">
		<span class="eyebrow">Erreur {page.status}</span>
		<h1 class="text-3xl leading-tight font-bold tracking-[-0.02em] sm:text-4xl">
			{forbidden ? 'Accès réservé' : notFound ? "Cette page n'existe pas" : 'Quelque chose a coincé'}
		</h1>
		<p class="text-lg text-ink-soft">
			{notFound ? "L'adresse est peut-être incomplète." : page.error?.message}
		</p>
		<div class="flex flex-wrap gap-2.5">
			{#if forbidden}
				<a href={USER_URL} class="btn btn-primary" data-sveltekit-reload>Aller sur Yimba</a>
				<button type="button" class="btn btn-ghost" onclick={logout}>Changer de compte</button>
			{:else}
				<a href={resolve('/(admin)')} class="btn btn-primary">Retour aux comptes</a>
				{#if !notFound}
					<button type="button" class="btn btn-ghost" onclick={() => location.reload()}>Réessayer</button>
				{/if}
			{/if}
		</div>
	</div>
</main>
