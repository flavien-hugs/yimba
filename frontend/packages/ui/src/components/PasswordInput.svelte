<script lang="ts">
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
	class="flex items-center rounded-field border-[1.5px] bg-white pr-1.5 focus-within:border-indigo {invalid
		? 'border-clay'
		: 'border-line'}"
>
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
		class="min-h-12 min-w-0 flex-1 bg-transparent px-3.5 text-[17px] text-ink outline-none"
	/>
	<button
		type="button"
		class="min-h-11 min-w-11 rounded-[6px] px-2 text-sm font-bold text-indigo hover:bg-indigo-wash"
		aria-controls={id}
		aria-pressed={visible}
		onclick={() => (visible = !visible)}
	>
		{visible ? 'Masquer' : 'Voir'}
	</button>
</div>
