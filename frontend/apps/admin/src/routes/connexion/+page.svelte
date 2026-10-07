<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError, session, type User } from '@yimba/api';
	import { AuthShell, LoginForm } from '@yimba/ui';

	// Where the user app is: the same site by default, another address when it has an image of its own.
	const USER_URL: string = import.meta.env.VITE_USER_URL || '/';

	let { data } = $props();

	async function enter(user: User) {
		if (user.role !== 'admin') {
			await session.logout();
			throw new ApiError(403, 'identity/not-admin', 'Not an admin');
		}
		await goto(data.next);
	}
</script>

<svelte:head>
	<title>Connexion · Administration Yimba</title>
</svelte:head>

<AuthShell title="Administration de Yimba">
	{#snippet intro()}
		<p class="max-w-[44ch] text-lg text-indigo-mist sm:text-[19px]">
			Les comptes de Yimba : qui y a accès, avec quel rôle. Réservé aux administrateurs.
		</p>
	{/snippet}

	<div class="flex flex-col gap-1.5">
		<h2 class="text-[30px] font-bold tracking-[-0.01em]">Connexion</h2>
		<p class="text-muted">Avec votre compte d'administrateur.</p>
	</div>
	<LoginForm onSuccess={enter} />
	<p class="text-center text-ink-soft">
		<a href={USER_URL} class="font-bold" data-sveltekit-reload>Aller sur Yimba</a>
	</p>
</AuthShell>
