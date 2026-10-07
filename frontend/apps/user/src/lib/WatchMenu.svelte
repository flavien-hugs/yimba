<!-- The watch picker of the header: a button that opens the list of watches, and a few related links. -->
<script lang="ts">
	import { Icon } from '@yimba/ui';

	interface Option {
		href: string;
		label: string;
		current: boolean;
		paused?: boolean;
	}

	interface Props {
		label: string;
		options: Option[];
		links?: { href: string; label: string }[];
		class?: string;
	}

	let { label, options, links = [], class: className = '' }: Props = $props();

	const uid = $props.id();
	let open = $state(false);
	let root = $state<HTMLDivElement>();
	let query = $state('');
	let filter = $state<HTMLInputElement>();
	$effect(() => filter?.focus());
	// Accents and case do not matter.
	const fold = (text: string) =>
		text
			.normalize('NFD')
			.replace(/\p{Diacritic}/gu, '')
			.toLowerCase();
	const shown = $derived(options.filter((option) => fold(option.label).includes(fold(query.trim()))));

	function closeOutside(event: MouseEvent) {
		if (open && root && !root.contains(event.target as Node)) open = false;
	}
</script>

<svelte:window
	onclick={closeOutside}
	onkeydown={(event) => open && event.key === 'Escape' && (open = false)}
/>

<div class="relative {className}" bind:this={root}>
	<button
		type="button"
		class="inline-flex min-h-11.5 w-full items-center justify-between gap-2 rounded-field border border-line bg-white px-4 text-[15px] font-bold hover:border-indigo"
		aria-expanded={open}
		aria-controls="{uid}-menu"
		onclick={() => {
			open = !open;
			query = '';
		}}
	>
		<span class="truncate">{label}</span>
		<Icon name="chevron" size={14} class={open ? 'rotate-180' : ''} />
	</button>

	{#if open}
		<div
			id="{uid}-menu"
			class="absolute right-0 z-40 mt-2 flex w-72 max-w-[calc(100vw-2rem)] flex-col gap-1 rounded-card border border-line bg-white p-2 shadow-[0_12px_32px_rgb(29_27_58/0.12)]"
		>
			<div class="flex min-h-11 items-center gap-2 rounded-field bg-lilac px-3">
				<Icon name="search" size={16} class="text-muted" />
				<input
					type="search"
					aria-label="Filtrer les veilles"
					placeholder="Rechercher une veille"
					autocomplete="off"
					bind:this={filter}
					bind:value={query}
					class="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
				/>
			</div>
			<ul class="flex max-h-60 flex-col gap-0.5 overflow-y-auto">
				{#each shown as option (option.href)}
					<li>
						<a
							href={option.href}
							aria-current={option.current ? 'true' : undefined}
							onclick={() => (open = false)}
							class="flex min-h-11 items-center justify-between gap-2 rounded-field px-3 font-semibold no-underline {option.current
								? 'bg-indigo-soft text-indigo-deep'
								: 'text-ink hover:bg-haze hover:text-ink'}"
						>
							<span class="truncate">{option.label}</span>
							{#if option.paused}<span class="tag bg-sand-soft text-sand-ink">en pause</span>{/if}
						</a>
					</li>
				{:else}
					<li class="px-3 py-3 text-muted">Aucune veille ne correspond.</li>
				{/each}
			</ul>
			{#if links.length}
				<hr class="my-1 border-line" />
				{#each links as link (link.href)}
					<a
						href={link.href}
						onclick={() => (open = false)}
						class="flex min-h-11 items-center rounded-field px-3 font-bold no-underline hover:bg-haze"
						>{link.label}</a
					>
				{/each}
			{/if}
		</div>
	{/if}
</div>
