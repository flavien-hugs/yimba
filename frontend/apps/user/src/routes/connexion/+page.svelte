<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { AuthShell, LoginForm } from '@yimba/ui';

	let { data } = $props();
</script>

<svelte:head>
	<title>Connexion · Yimba</title>
</svelte:head>

<AuthShell title="Écouter pour mieux décider">
	{#snippet intro()}
		<p class="max-w-[44ch] text-lg text-indigo-mist sm:text-[19px]">
			Yimba rassemble ce que les gens disent, ressentent et craignent, pour que chaque décision parte de leurs
			préoccupations réelles.
		</p>
	{/snippet}

	<div class="flex flex-col gap-1.5">
		<h2 class="text-[30px] font-bold tracking-[-0.01em]">Content de vous revoir</h2>
		<p class="text-muted">Connectez-vous pour retrouver vos veilles.</p>
	</div>
	<LoginForm onSuccess={() => goto(data.next)} />
	<p class="text-center text-ink-soft">
		Pas encore de compte ? <a href={resolve('/inscription')} class="font-bold">Créer un compte</a>
	</p>
</AuthShell>
