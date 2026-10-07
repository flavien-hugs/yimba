<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { describe, session } from '@yimba/api';
	import {
		Icon,
		Notice,
		PasswordInput,
		PasswordStrength,
		formatDate,
		formatMoment,
		initials
	} from '@yimba/ui';

	let { data } = $props();

	const user = $derived(session.user ?? data.user);

	let current = $state('');
	let next = $state('');
	let again = $state('');
	let busy = $state(false);
	let error = $state('');
	let done = $state(false);

	async function changePassword(event: SubmitEvent) {
		event.preventDefault();
		done = false;
		if (next !== again) {
			error = 'Les deux nouveaux mots de passe ne sont pas identiques.';
			return;
		}
		busy = true;
		error = '';
		try {
			await session.changePassword(current, next);
			current = next = again = '';
			done = true;
		} catch (caught) {
			error = describe(caught);
		} finally {
			busy = false;
		}
	}

	async function logout() {
		await session.logout();
		await goto(resolve('/connexion'));
	}
</script>

<svelte:head>
	<title>Mon compte · Yimba</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-[760px] flex-col gap-5">
	<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">Mon compte</h1>

	<section class="card flex flex-wrap items-center gap-5" aria-label="Profil">
		<span
			class="flex size-16 shrink-0 items-center justify-center rounded-full bg-indigo font-display text-2xl font-bold text-white"
			aria-hidden="true">{initials(user.full_name, user.email)}</span
		>
		<div class="flex min-w-0 flex-1 flex-col">
			<span class="text-xl font-bold">{user.full_name ?? user.email}</span>
			<span class="break-all text-muted">{user.email}</span>
			<span class="text-sm text-muted">
				{user.role === 'admin' ? 'Administrateur' : 'Utilisateur'} · membre depuis le {formatDate(
					user.created_at
				)}
				{#if user.last_login_at}· dernière connexion {formatMoment(user.last_login_at)}{/if}
			</span>
		</div>
		<div class="flex flex-wrap gap-2.5">
			{#if user.role === 'admin'}
				<a href="/admin/" class="btn btn-soft" data-sveltekit-reload>Administration</a>
			{/if}
			<button type="button" class="btn btn-ghost" onclick={logout}>
				<Icon name="logout" size={18} /> Se déconnecter
			</button>
		</div>
	</section>

	<section class="card flex flex-col gap-4 sm:p-8" aria-labelledby="password-title">
		<div class="flex flex-col gap-1">
			<h2 id="password-title" class="text-2xl font-semibold">Changer de mot de passe</h2>
			<p class="text-muted">Vos autres sessions seront fermées ; celle-ci reste ouverte.</p>
		</div>
		<form class="flex flex-col gap-3.5" onsubmit={changePassword}>
			{#if error}
				<Notice tone="danger">{error}</Notice>
			{/if}
			{#if done}
				<Notice tone="success">Mot de passe changé. Les autres appareils devront se reconnecter.</Notice>
			{/if}
			<div class="flex flex-col gap-1.5">
				<label for="current-password" class="font-bold">Mot de passe actuel</label>
				<PasswordInput id="current-password" autocomplete="current-password" bind:value={current} />
			</div>
			<div class="flex flex-col gap-1.5">
				<label for="next-password" class="font-bold">Nouveau mot de passe</label>
				<PasswordInput
					id="next-password"
					autocomplete="new-password"
					describedby="next-strength"
					bind:value={next}
				/>
				<PasswordStrength id="next-strength" password={next} />
			</div>
			<div class="flex flex-col gap-1.5">
				<label for="again-password" class="font-bold">Encore une fois</label>
				<PasswordInput
					id="again-password"
					autocomplete="new-password"
					invalid={again.length > 0 && again !== next}
					bind:value={again}
				/>
			</div>
			<button type="submit" class="btn btn-primary self-start" disabled={busy}>
				{busy ? 'Un instant…' : 'Enregistrer le mot de passe'}
			</button>
		</form>
	</section>
</div>
