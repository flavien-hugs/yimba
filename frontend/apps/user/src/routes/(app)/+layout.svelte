<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { session } from '@yimba/api';
	import { Icon, Logo, Pagne, initials, type IconName } from '@yimba/ui';
	import { loginUrl } from '#lib/load.js';
	import { currentWatch, rememberWatch, withQuery } from '#lib/watch.js';
	import WatchMenu from '#lib/WatchMenu.svelte';

	let { data, children } = $props();

	const user = $derived(session.user ?? data.user);
	const routeId = $derived(page.route.id ?? '');
	// Creating or editing a watch: the header keeps only "Fermer" and the account (design: "Nouvelle veille").
	const focused = $derived(routeId.startsWith('/(app)/veilles/'));
	const onAlerts = $derived(routeId === '/(app)/alertes');
	const watch = $derived(currentWatch(data.watches, page.url));
	const veille = $derived(watch?.id);

	$effect(() => {
		if (veille) rememberWatch(veille);
	});

	const home = resolve('/(app)');
	const nav = $derived<{ href: string; path: string; label: string; short: string; icon: IconName }[]>([
		{ path: home, href: withQuery(home, { veille }), label: 'Accueil', short: 'Accueil', icon: 'home' },
		{
			path: resolve('/(app)/paroles'),
			href: withQuery(resolve('/(app)/paroles'), { veille }),
			label: 'Paroles',
			short: 'Paroles',
			icon: 'chat'
		},
		{
			path: resolve('/(app)/alertes'),
			href: resolve('/(app)/alertes'),
			label: 'Alertes',
			short: 'Alertes',
			icon: 'bell'
		},
		{
			path: resolve('/(app)/veilles'),
			href: resolve('/(app)/veilles'),
			label: 'Mes veilles',
			short: 'Veilles',
			icon: 'list'
		},
		{
			path: resolve('/(app)/veilles/nouvelle'),
			href: resolve('/(app)/veilles/nouvelle'),
			label: 'Nouvelle veille',
			short: 'Créer',
			icon: 'plus'
		}
	]);

	const watches = resolve('/(app)/veilles');
	const creation = resolve('/(app)/veilles/nouvelle');
	const isCurrent = (path: string) => {
		const here = page.url.pathname;
		if (path === creation) return here === creation;
		// The list stands for the settings of a watch too, not for the creation.
		if (path === watches) return here.startsWith(watches) && here !== creation;
		return path === home ? here === home : here.startsWith(path);
	};

	// The header's watch button: picks the watch shown, or, on the alerts, filters them.
	const menu = $derived.by(() => {
		if (onAlerts) {
			const alerts = resolve('/(app)/alertes');
			const filter = page.url.searchParams.get('veille');
			return {
				label: data.watches.find((option) => option.id === filter)?.name ?? 'Toutes les veilles',
				options: [
					{ href: alerts, label: 'Toutes les veilles', current: !filter },
					...data.watches.map((option) => ({
						href: withQuery(alerts, { veille: option.id }),
						label: option.name,
						current: option.id === filter,
						paused: !option.active
					}))
				],
				links: []
			};
		}
		// The filters of one watch do not apply to another: keep the page, drop the rest.
		const target = routeId === '/(app)/paroles' ? page.url.pathname : home;
		return {
			label: watch?.name ?? 'Choisir une veille',
			options: data.watches.map((option) => ({
				href: withQuery(target, { veille: option.id }),
				label: option.name,
				current: option.id === veille,
				paused: !option.active
			})),
			links: [
				...(watch
					? [{ href: resolve('/(app)/veilles/[id]', { id: watch.id }), label: 'Réglages de cette veille' }]
					: []),
				{ href: resolve('/(app)/veilles/nouvelle'), label: 'Nouvelle veille' }
			]
		};
	});

	// The side menu can be folded down to its icons; the choice is kept on this device.
	const FOLDED = 'yimba.menu-replie';
	let folded = $state(readFolded());

	function readFolded(): boolean {
		try {
			return localStorage.getItem(FOLDED) === '1';
		} catch {
			return false;
		}
	}

	function toggleMenu() {
		folded = !folded;
		try {
			localStorage.setItem(FOLDED, folded ? '1' : '0');
		} catch {
			// storage blocked: the choice lasts until the page is reloaded
		}
	}

	async function logout() {
		await session.logout();
		await goto(loginUrl());
	}
</script>

<div class="flex min-h-dvh flex-col">
	<div class="sticky top-0 z-30">
		<header class="flex flex-wrap items-center gap-x-5 gap-y-3 bg-white px-4 py-2.5 sm:px-7 md:py-3">
			<a href={withQuery(home, { veille })} class="no-underline" aria-label="Yimba, accueil">
				<span class="md:hidden"><Logo size="sm" /></span>
				<span class="hidden md:inline"><Logo /></span>
			</a>

			{#if !focused}
				<form
					role="search"
					action={resolve('/(app)/paroles')}
					method="get"
					class="hidden min-h-11.5 max-w-[520px] flex-[1_1_260px] items-center gap-2.5 rounded-field bg-lilac px-4 md:flex"
				>
					<Icon name="search" size={18} class="text-muted" />
					<label for="header-search" class="sr-only">Rechercher une conversation</label>
					<input
						id="header-search"
						name="q"
						type="search"
						placeholder="Chercher une conversation, un mot, un lieu"
						class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted"
					/>
					{#if veille}<input type="hidden" name="veille" value={veille} />{/if}
				</form>
			{/if}

			<div class="ml-auto flex items-center gap-2 md:gap-3">
				{#if focused}
					<a href={withQuery(home, { veille })} class="btn btn-ghost min-h-11.5 px-4.5">Fermer</a>
				{:else}
					{#if data.watches.length > 0}
						<WatchMenu class="hidden max-w-64 md:block" {...menu} />
					{/if}
					<a
						href={resolve('/(app)/alertes')}
						class="relative flex size-11 items-center justify-center rounded-full bg-sun-soft text-sun-deep hover:text-sun-ink md:size-11.5"
						aria-label={data.openAlertCount ? `Alertes, ${data.openAlertCount} à traiter` : 'Alertes'}
					>
						<Icon name="bell" />
						{#if data.openAlertCount}
							<span
								class="absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-clay px-1 text-xs font-bold text-white"
								aria-hidden="true">{data.openAlertCount}</span
							>
						{/if}
					</a>
				{/if}
				<a
					href={resolve('/(app)/compte')}
					class="flex size-11 items-center justify-center rounded-full bg-indigo font-display text-[15px] font-bold text-white no-underline hover:bg-indigo-deep hover:text-white md:size-11.5 md:text-base"
					aria-label="Mon compte ({user.full_name ?? user.email})"
				>
					{initials(user.full_name, user.email)}
				</a>
			</div>
		</header>
		<Pagne />
	</div>

	{#if !focused && data.watches.length > 0}
		<div class="px-4 pt-4 md:hidden">
			<WatchMenu class="w-full" {...menu} />
		</div>
	{/if}

	<div class="flex flex-1 items-stretch">
		<nav
			aria-label="Navigation principale"
			class="sticky top-20 hidden h-[calc(100dvh-5rem)] shrink-0 flex-col gap-1 self-start overflow-x-hidden overflow-y-auto px-3 py-5 transition-[width] duration-200 md:flex {folded
				? 'w-19'
				: 'w-60'}"
		>
			{#each nav as item (item.path)}
				{@const current = isCurrent(item.path)}
				<a
					href={item.href}
					aria-label={item.label}
					title={item.label}
					aria-current={current ? 'page' : undefined}
					class="flex min-h-12 items-center gap-3 rounded-field px-3.5 text-[15px] font-bold whitespace-nowrap no-underline {current
						? 'bg-indigo-soft text-indigo-deep hover:text-indigo-deep'
						: 'text-muted hover:bg-haze hover:text-ink'}"
				>
					<Icon name={item.icon} />
					{#if !folded}<span>{item.label}</span>{/if}
				</a>
			{/each}
			<hr class="mt-auto mb-3 w-full border-line" />
			<div class="flex gap-1 {folded ? 'flex-col-reverse items-start' : 'items-center'}">
				<button
					type="button"
					aria-label="Se déconnecter"
					title="Se déconnecter"
					class="flex min-h-12 min-w-0 flex-auto items-center gap-3 rounded-field px-3.5 text-[15px] font-bold whitespace-nowrap text-clay-ink hover:bg-clay-soft"
					onclick={logout}
				>
					<Icon name="logout" />
					{#if !folded}<span>Se déconnecter</span>{/if}
				</button>
				<button
					type="button"
					aria-label={folded ? 'Déplier le menu' : 'Réduire le menu'}
					title={folded ? 'Déplier le menu' : 'Réduire le menu'}
					aria-expanded={!folded}
					class="flex h-12 w-11 shrink-0 items-center justify-center rounded-field text-muted hover:bg-haze {folded
						? 'ml-[3px]'
						: ''}"
					onclick={toggleMenu}
				>
					<Icon name={folded ? 'panel-expand' : 'panel-collapse'} />
				</button>
			</div>
		</nav>

		<main
			class="min-w-0 flex-1 px-4 pb-28 sm:px-7 md:pr-7 md:pb-12 md:pl-2 {focused
				? 'pt-8 md:pb-14'
				: 'pt-4 md:pt-6'}"
		>
			{@render children()}
		</main>
	</div>

	<nav
		aria-label="Navigation principale"
		class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 rounded-t-card bg-white px-2 pt-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] shadow-[0_-6px_24px_rgb(29_27_58/0.08)] md:hidden"
	>
		{#each nav as item (item.path)}
			<a
				href={item.href}
				aria-current={isCurrent(item.path) ? 'page' : undefined}
				class="flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-field text-xs font-bold no-underline {isCurrent(
					item.path
				)
					? 'bg-indigo-soft text-indigo-deep'
					: 'text-muted'}"
			>
				<Icon name={item.icon} />
				{item.short}
			</a>
		{/each}
	</nav>
</div>
