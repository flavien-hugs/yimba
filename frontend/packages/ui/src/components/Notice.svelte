<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		tone?: 'info' | 'success' | 'warning' | 'danger';
		class?: string;
		children: Snippet;
	}

	let { tone = 'info', class: className = '', children }: Props = $props();

	const TONES = {
		info: 'bg-indigo-soft text-indigo-deep',
		success: 'bg-leaf-soft text-leaf-ink',
		warning: 'bg-sun-soft text-sun-text',
		danger: 'bg-clay-soft text-clay-ink'
	};
</script>

<p
	class="m-0 rounded-field px-3.5 py-3 text-[15px] {TONES[tone]} {className}"
	role={tone === 'danger' ? 'alert' : 'status'}
>
	{@render children()}
</p>
