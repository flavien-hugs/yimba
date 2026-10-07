<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, describe, session } from '@yimba/api';
	import { AuthShell, Icon, IconInput, Notice, PasswordInput, PasswordStrength } from '@yimba/ui';

	const PROMISES = [
		'Voyez ce que les gens disent, dans leurs mots, en français comme en nouchi.',
		'Soyez prévenu·e quand l’opinion se tend, avant que la crise ne s’installe.',
		'Chaque personne reste anonyme : vous lisez des paroles, jamais des identités.'
	];

	let fullName = $state('');
	let email = $state('');
	let password = $state('');
	let busy = $state(false);
	let error = $state('');

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		try {
			await api.register({ email, password, full_name: fullName.trim() || null });
			await session.login(email, password, false);
			// A new account has no watch yet: start with the first one.
			await goto(resolve('/(app)/veilles/nouvelle'));
		} catch (caught) {
			error = describe(caught);
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Créer un compte · Yimba</title>
</svelte:head>

<AuthShell title="Rejoignez ceux qui écoutent">
	{#snippet intro()}
		<ul class="flex max-w-[46ch] flex-col gap-3.5">
			{#each PROMISES as promise (promise)}
				<li class="flex items-start gap-3.5 text-lg text-indigo-mist">
					<span class="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-sun text-ink">
						<Icon name="check" size={16} />
					</span>
					{promise}
				</li>
			{/each}
		</ul>
	{/snippet}

	<div class="flex flex-col gap-1.5">
		<h2 class="text-[30px] font-bold tracking-[-0.01em]">Créer votre compte</h2>
		<p class="text-muted">Trois informations, et vous créez votre première veille.</p>
	</div>

	<form class="flex flex-col gap-3.5" onsubmit={submit}>
		{#if error}
			<Notice tone="danger">{error}</Notice>
		{/if}
		<label class="label">
			Nom complet
			<IconInput icon="user" autocomplete="name" maxlength={200} bind:value={fullName} />
		</label>
		<label class="label">
			Courriel professionnel
			<IconInput icon="mail" type="email" autocomplete="email" required bind:value={email} />
		</label>
		<div class="flex flex-col gap-1.5">
			<label for="new-password" class="font-bold">Mot de passe</label>
			<PasswordInput
				id="new-password"
				autocomplete="new-password"
				describedby="password-strength"
				bind:value={password}
			/>
			<PasswordStrength id="password-strength" {password} />
		</div>
		<button type="submit" class="btn btn-primary min-h-13.5 text-[17px]" disabled={busy}>
			{busy ? 'Création…' : 'Créer mon compte'}
		</button>
	</form>

	<p class="text-sm text-muted">
		Les personnes citées dans Yimba restent anonymes : vous lisez des paroles, pas des profils.
	</p>
	<p class="text-center text-ink-soft">
		Déjà un compte ? <a href={resolve('/connexion')} class="font-bold">Se connecter</a>
	</p>
</AuthShell>
