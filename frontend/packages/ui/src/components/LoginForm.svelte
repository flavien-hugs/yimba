<!-- Email and password login, shared by the user app and the admin app. -->
<script lang="ts">
	import { describe, session, type User } from '@yimba/api';
	import Notice from './Notice.svelte';
	import PasswordInput from './PasswordInput.svelte';

	interface Props {
		onSuccess: (user: User) => unknown;
	}

	let { onSuccess }: Props = $props();

	let email = $state('');
	let password = $state('');
	let remember = $state(true);
	let busy = $state(false);
	let error = $state('');

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		try {
			await onSuccess(await session.login(email, password, remember));
		} catch (caught) {
			error = describe(caught);
		} finally {
			busy = false;
		}
	}
</script>

<form class="flex flex-col gap-3.5" onsubmit={submit}>
	{#if error}
		<Notice tone="danger">{error}</Notice>
	{/if}
	<label class="label">
		Courriel
		<input class="field" type="email" autocomplete="username" required bind:value={email} />
	</label>
	<div class="flex flex-col gap-1.5">
		<label for="login-password" class="font-bold">Mot de passe</label>
		<PasswordInput id="login-password" autocomplete="current-password" bind:value={password} />
	</div>
	<label class="flex min-h-11 items-center gap-2.5 font-semibold">
		<input type="checkbox" class="size-5.5 accent-indigo" bind:checked={remember} />
		Rester connecté·e sur cet appareil
	</label>
	<button type="submit" class="btn btn-primary min-h-13.5 text-[17px]" disabled={busy}>
		{busy ? 'Connexion…' : 'Se connecter'}
	</button>
</form>
