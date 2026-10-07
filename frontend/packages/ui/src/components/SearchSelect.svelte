<!-- A select with a search field: type to filter the options, arrows and Enter to choose, Escape to close. -->
<script lang="ts">
	import Icon from './Icon.svelte';

	interface Option {
		value: string;
		label: string;
	}

	interface Props {
		options: Option[];
		value: string;
		/** Names the control for screen readers when no <label for> points at it. */
		label?: string;
		id?: string;
		placeholder?: string;
		disabled?: boolean;
		/** field: a form field; pill: compact, for tables and toolbars. */
		variant?: 'field' | 'pill';
		onchange?: (value: string) => void;
	}

	let {
		options,
		value = $bindable(),
		label,
		id,
		placeholder = 'Rechercher',
		disabled = false,
		variant = 'field',
		onchange
	}: Props = $props();

	const uid = $props.id();
	let open = $state(false);
	let query = $state('');
	let active = $state(0);
	let root = $state<HTMLDivElement>();
	let search = $state<HTMLInputElement>();
	let trigger = $state<HTMLButtonElement>();

	const selected = $derived(options.find((option) => option.value === value));
	// Accents and case do not matter: "cote" finds "Côte d'Ivoire".
	const fold = (text: string) =>
		text
			.normalize('NFD')
			.replace(/\p{Diacritic}/gu, '')
			.toLowerCase();
	const shown = $derived(options.filter((option) => fold(option.label).includes(fold(query.trim()))));

	function show() {
		query = '';
		active = Math.max(
			0,
			options.findIndex((option) => option.value === value)
		);
		open = true;
		queueMicrotask(() => search?.focus());
	}

	function close(refocus = true) {
		open = false;
		if (refocus) trigger?.focus();
	}

	function choose(option: Option) {
		value = option.value;
		onchange?.(option.value);
		close();
	}

	function onkeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') active = Math.min(active + 1, shown.length - 1);
		else if (event.key === 'ArrowUp') active = Math.max(active - 1, 0);
		else if (event.key === 'Enter' && shown[active]) choose(shown[active]);
		else if (event.key === 'Escape') close();
		else if (event.key === 'Tab') close(false);
		else return;
		event.preventDefault();
	}

	$effect(() => {
		query;
		active = 0;
	});
</script>

<svelte:window onclick={(event) => open && root && !root.contains(event.target as Node) && close(false)} />

<div class="relative" bind:this={root}>
	<button
		{id}
		bind:this={trigger}
		type="button"
		{disabled}
		role="combobox"
		aria-haspopup="listbox"
		aria-expanded={open}
		aria-controls="{uid}-list"
		aria-label={label}
		class="flex w-full items-center justify-between gap-2 border bg-white text-left disabled:opacity-60 {variant ===
		'field'
			? 'field min-h-13'
			: 'min-h-11 rounded-field border-line px-3 font-semibold hover:border-indigo'}"
		onclick={() => (open ? close() : show())}
	>
		<span class="truncate">{selected?.label ?? ''}</span>
		<Icon name="chevron" size={14} class="text-muted {open ? 'rotate-180' : ''}" />
	</button>

	{#if open}
		<div
			class="absolute left-0 z-40 mt-2 flex min-w-full flex-col gap-1 rounded-card border border-line bg-white p-2 shadow-[0_12px_32px_rgb(29_27_58/0.12)] {variant ===
			'pill'
				? 'w-64'
				: 'w-full'}"
		>
			<div class="flex min-h-11 items-center gap-2 rounded-field bg-lilac px-3">
				<Icon name="search" size={16} class="text-muted" />
				<input
					bind:this={search}
					bind:value={query}
					{onkeydown}
					type="search"
					aria-label="Filtrer les options"
					aria-controls="{uid}-list"
					aria-activedescendant={shown[active] ? `${uid}-${active}` : undefined}
					{placeholder}
					autocomplete="off"
					class="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
				/>
			</div>
			<ul id="{uid}-list" role="listbox" aria-label={label} class="max-h-60 overflow-y-auto">
				{#each shown as option, index (option.value)}
					<!-- Keyboard use goes through the search field (aria-activedescendant), as in any combobox. -->
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<li
						id="{uid}-{index}"
						role="option"
						aria-selected={option.value === value}
						class="flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-field px-3 font-semibold {index ===
						active
							? 'bg-haze'
							: ''} {option.value === value ? 'text-indigo-deep' : ''}"
						onmouseenter={() => (active = index)}
						onclick={() => choose(option)}
					>
						<span class="truncate">{option.label}</span>
						{#if option.value === value}<Icon name="check" size={16} />{/if}
					</li>
				{:else}
					<li class="px-3 py-3 text-muted" role="presentation">Aucun résultat</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
