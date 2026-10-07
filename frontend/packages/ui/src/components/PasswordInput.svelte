<script lang="ts">
	import Icon from './Icon.svelte';
	interface Props {
		id: string;
		value?: string;
		autocomplete: 'current-password' | 'new-password';
		required?: boolean;
		invalid?: boolean;
		describedby?: string;
	}

	let {
		id,
		value = $bindable(''),
		autocomplete,
		required = true,
		invalid = false,
		describedby
	}: Props = $props();
	let visible = $state(false);
</script>

<div
	class="flex items-center gap-2.5 rounded-field border-[1.5px] bg-white pr-1.5 pl-3.5 focus-within:border-indigo {invalid
		? 'border-clay'
		: 'border-line'}"
>
	<Icon name="lock" size={20} class="text-muted" />
	<input
		{id}
		type={visible ? 'text' : 'password'}
		{value}
		oninput={(event) => (value = event.currentTarget.value)}
		{autocomplete}
		{required}
		aria-invalid={invalid}
		aria-describedby={describedby}
		spellcheck="false"
		class="min-h-12 min-w-0 flex-1 bg-transparent text-[17px] text-ink outline-none"
	/>
	<button
		type="button"
		class="flex size-11 items-center justify-center rounded-[6px] text-indigo hover:bg-indigo-wash"
		aria-controls={id}
		aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
		title={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
		onclick={() => (visible = !visible)}
	>
		<Icon name={visible ? 'eye-off' : 'eye'} />
	</button>
</div>
