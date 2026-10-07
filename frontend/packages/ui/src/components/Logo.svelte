<script lang="ts">
	interface Props {
		size?: 'sm' | 'md' | 'lg';
		/** White disc, for the indigo panels. */
		inverted?: boolean;
		class?: string;
	}

	let { size = 'md', inverted = false, class: className = '' }: Props = $props();

	const SIZES = {
		sm: { mark: 32, text: 'text-2xl' },
		md: { mark: 36, text: 'text-[26px]' },
		lg: { mark: 40, text: 'text-[30px]' }
	};
	const { mark, text } = $derived(SIZES[size]);
</script>

<span class="inline-flex items-center gap-2.5 {className}">
	<svg width={mark} height={mark} viewBox="0 0 36 36" fill="none" aria-hidden="true">
		<circle cx="18" cy="18" r="18" class={inverted ? 'fill-white' : 'fill-indigo'} />
		<circle cx="18" cy="15" r="6" class="fill-sun" />
		<path
			d="M8 25c3-3 5-3 10 0s7 3 10 0"
			class={inverted ? 'stroke-indigo' : 'stroke-white'}
			stroke-width="2.4"
			stroke-linecap="round"
		/>
	</svg>
	<span class="font-display font-bold tracking-[-0.01em] {text} {inverted ? 'text-white' : 'text-indigo'}"
		>Yimba</span
	>
</span>
