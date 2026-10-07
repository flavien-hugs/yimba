<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { session } from '@yimba/api';
	import { Icon, Logo, Pagne, initials } from '@yimba/ui';

	let { data, children } = $props();

	const user = $derived(session.user ?? data.user);

	async function logout() {
		await session.logout();
		await goto(resolve('/connexion'));
	}
</script>

<div class="flex min-h-dvh flex-col">
	<header class="flex flex-wrap items-center gap-x-4 gap-y-3 bg-white px-4 py-3 sm:px-7">
		<a
			href={resolve('/(admin)')}
			class="flex items-center gap-3 no-underline"
			aria-label="Administration de Yimba"
		>
			<Logo />
			<span class="tag bg-sun-soft text-sun-ink">Administration</span>
		</a>
		<div class="ml-auto flex items-center gap-2.5">
			<a href="/" class="btn btn-ghost min-h-11.5 px-4" data-sveltekit-reload>Aller sur Yimba</a>
			<span
				class="hidden size-11.5 items-center justify-center rounded-full bg-indigo font-display font-bold text-white sm:flex"
				title={user.full_name ?? user.email}
				aria-hidden="true">{initials(user.full_name, user.email)}</span
			>
			<button type="button" class="btn btn-ghost min-h-11.5 px-4" onclick={logout}>
				<Icon name="logout" size={18} /><span class="sr-only sm:not-sr-only">Se déconnecter</span>
			</button>
		</div>
	</header>
	<Pagne />
	<main class="mx-auto w-full max-w-[1200px] flex-1 px-4 py-6 sm:px-7">
		{@render children()}
	</main>
</div>
