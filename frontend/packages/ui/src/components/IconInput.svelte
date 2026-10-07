<!-- A text field with a descriptive icon in front of it: an envelope for the email, a person for the name... -->
<script lang="ts">
	import Icon, { type IconName } from './Icon.svelte';

	interface Props {
		icon: IconName;
		value?: string;
		type?: 'text' | 'email';
		id?: string;
		autocomplete?: 'name' | 'email' | 'username';
		required?: boolean;
		maxlength?: number;
		placeholder?: string;
		invalid?: boolean;
	}

	let {
		icon,
		value = $bindable(''),
		type = 'text',
		id,
		autocomplete,
		required = false,
		maxlength,
		placeholder,
		invalid = false
	}: Props = $props();
</script>

<div
	class="flex items-center gap-2.5 rounded-field border-[1.5px] bg-white pl-3.5 focus-within:border-indigo {invalid
		? 'border-clay'
		: 'border-line'}"
>
	<Icon name={icon} size={20} class="text-muted" />
	<input
		{id}
		{type}
		{autocomplete}
		{required}
		{maxlength}
		{placeholder}
		aria-invalid={invalid}
		bind:value
		class="min-h-12 min-w-0 flex-1 bg-transparent pr-3.5 text-[17px] text-ink outline-none"
	/>
</div>
