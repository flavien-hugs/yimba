<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import { api, describe, type Role, type User } from '@yimba/api';
	import { Icon, Notice, SearchSelect, formatDate, formatMoment, formatNumber, plural } from '@yimba/ui';

	let { data } = $props();

	let pending = $state<string | null>(null);
	let confirming = $state<string | null>(null);
	let error = $state('');
	let notice = $state('');

	/** This address with some parameters changed; null removes one. */
	function changed(changes: Record<string, string | null>): string {
		const params = new URLSearchParams(page.url.search);
		for (const [key, value] of Object.entries(changes)) {
			if (value === null) params.delete(key);
			else params.set(key, value);
		}
		const search = params.toString();
		return search ? `?${search}` : page.url.pathname;
	}

	async function act(user: User, run: () => Promise<unknown>, done: string): Promise<boolean> {
		pending = user.id;
		error = '';
		notice = '';
		try {
			await run();
			await invalidate('yimba:users');
			notice = done;
			return true;
		} catch (caught) {
			error = describe(caught);
			return false;
		} finally {
			pending = null;
		}
	}

	// Bumped when a change is refused, so that the select shows the role the account still has.
	let roleResets = $state(0);

	async function setRole(user: User, role: Role) {
		const ok = await act(
			user,
			() => api.users.update(user.id, { role }),
			`${user.email} est maintenant ${ROLES[role].toLowerCase()}.`
		);
		if (!ok) roleResets += 1;
	}

	const toggleActive = (user: User) =>
		act(
			user,
			() => api.users.update(user.id, { active: !user.active }),
			user.active ? `${user.email} ne peut plus se connecter.` : `${user.email} peut de nouveau se connecter.`
		);

	async function remove(user: User) {
		confirming = null;
		await act(
			user,
			() => api.users.remove(user.id),
			`Le compte ${user.email} est supprimé ; ses veilles sont en pause.`
		);
	}

	const ROLES: Record<Role, string> = { user: 'Utilisateur', admin: 'Administrateur' };
</script>

<svelte:head>
	<title>Comptes · Administration Yimba</title>
</svelte:head>

<div class="flex flex-col gap-5">
	<header class="flex flex-col gap-1">
		<h1 class="text-[32px] leading-[1.12] font-bold tracking-[-0.02em] sm:text-4xl">Comptes</h1>
		<p class="text-[17px] text-muted">
			{plural(data.users.total, 'compte')}{data.search ? ` pour « ${data.search} »` : ''}{data.withDeleted
				? ', supprimés compris'
				: ''}. Un compte désactivé ou supprimé ne peut plus se connecter ; ses sessions s'arrêtent aussitôt.
		</p>
	</header>

	<div class="flex flex-wrap items-center gap-3">
		<form
			method="get"
			role="search"
			class="flex min-h-11.5 flex-[1_1_280px] items-center gap-2.5 rounded-field bg-white px-4 sm:max-w-md"
		>
			<Icon name="search" size={18} class="text-muted" />
			<label for="user-search" class="sr-only">Chercher un compte par courriel</label>
			<input
				id="user-search"
				name="q"
				type="search"
				value={data.search}
				placeholder="Chercher par courriel"
				class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted"
			/>
			{#if data.withDeleted}<input type="hidden" name="supprimes" value="1" />{/if}
		</form>
		<a
			href={changed({ supprimes: data.withDeleted ? null : '1', page: null })}
			class="chip min-h-11.5"
			aria-current={data.withDeleted ? 'true' : undefined}
		>
			Afficher les comptes supprimés
		</a>
	</div>

	{#if error}
		<Notice tone="danger">{error}</Notice>
	{/if}
	{#if notice}
		<Notice tone="success">{notice}</Notice>
	{/if}

	<div class="overflow-x-auto rounded-card bg-white">
		<table class="w-full min-w-[820px] border-collapse text-left">
			<caption class="sr-only">Comptes de Yimba</caption>
			<thead>
				<tr class="border-b border-rule text-sm text-muted">
					<th scope="col" class="px-5 py-3.5 font-bold">Personne</th>
					<th scope="col" class="px-3 py-3.5 font-bold">Rôle</th>
					<th scope="col" class="px-3 py-3.5 font-bold">Accès</th>
					<th scope="col" class="px-3 py-3.5 font-bold">Dernière connexion</th>
					<th scope="col" class="px-3 py-3.5 font-bold">Créé le</th>
					<th scope="col" class="px-5 py-3.5 font-bold"><span class="sr-only">Actions</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.users.items as user (user.id)}
					{@const self = user.id === data.user.id}
					{@const deleted = user.deleted_at !== null}
					{@const busy = pending === user.id}
					<tr class="border-b border-rule last:border-0 {deleted ? 'text-muted' : ''}">
						<td class="px-5 py-3.5">
							<div class="flex flex-col">
								<span class="font-bold">
									{user.full_name ?? '—'}
									{#if self}<span class="tag ml-1 bg-indigo-soft text-indigo-deep">Vous</span>{/if}
								</span>
								<span class="text-sm break-all">{user.email}</span>
							</div>
						</td>
						<td class="px-3 py-3.5">
							{#if deleted || self}
								{ROLES[user.role]}
							{:else}
								{#key `${user.id}-${user.role}-${roleResets}`}
									<SearchSelect
										variant="pill"
										label="Rôle de {user.email}"
										value={user.role}
										disabled={busy}
										options={Object.entries(ROLES).map(([value, label]) => ({ value, label }))}
										onchange={(role) => setRole(user, role as Role)}
									/>
								{/key}
							{/if}
						</td>
						<td class="px-3 py-3.5">
							{#if deleted}
								<span class="tag bg-clay-soft text-clay-ink">Supprimé le {formatDate(user.deleted_at!)}</span>
							{:else if user.active}
								<span class="tag bg-leaf-soft text-leaf-ink">Actif</span>
							{:else}
								<span class="tag bg-sand-soft text-sand-ink">Désactivé</span>
							{/if}
						</td>
						<td class="px-3 py-3.5 text-sm"
							>{user.last_login_at ? formatMoment(user.last_login_at) : 'Jamais'}</td
						>
						<td class="px-3 py-3.5 text-sm">{formatDate(user.created_at)}</td>
						<td class="px-5 py-3.5">
							{#if !deleted && !self}
								{#if confirming === user.id}
									<div class="flex flex-wrap items-center justify-end gap-2" role="alert">
										<span class="text-sm text-clay-ink">Supprimer ? Ses veilles passent en pause.</span>
										<button
											type="button"
											class="btn btn-danger min-h-11 px-4"
											disabled={busy}
											onclick={() => remove(user)}
										>
											Supprimer
										</button>
										<button
											type="button"
											class="btn btn-ghost min-h-11 px-4"
											onclick={() => (confirming = null)}>Annuler</button
										>
									</div>
								{:else}
									<div class="flex flex-wrap justify-end gap-2">
										<button
											type="button"
											class="btn btn-ghost min-h-11 px-4"
											disabled={busy}
											onclick={() => toggleActive(user)}
										>
											{user.active ? 'Désactiver' : 'Réactiver'}
										</button>
										<button
											type="button"
											class="btn btn-ghost min-h-11 px-4 text-clay"
											disabled={busy}
											onclick={() => (confirming = user.id)}
										>
											Supprimer
										</button>
									</div>
								{/if}
							{/if}
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan="6" class="px-5 py-8 text-center text-muted">Aucun compte ne correspond.</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if data.pages > 1}
		{@const current = data.users.page}
		<nav class="flex flex-wrap items-center justify-center gap-3" aria-label="Pages">
			{#if current > 1}
				<a href={changed({ page: String(current - 1) })} class="btn btn-ghost">Précédente</a>
			{/if}
			<span class="text-muted">Page {formatNumber(current)} sur {formatNumber(data.pages)}</span>
			{#if current < data.pages}
				<a href={changed({ page: String(current + 1) })} class="btn btn-ghost">Suivante</a>
			{/if}
		</nav>
	{/if}
</div>
