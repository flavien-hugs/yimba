<!-- Authentication pages: the indigo panel on the left (stacked on top on a phone), the form card on the right. -->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import Baobab from './Baobab.svelte';
	import Logo from './Logo.svelte';
	import Pagne from './Pagne.svelte';

	interface Props {
		title: string;
		/** Under the title, in the panel. */
		intro?: Snippet;
		children: Snippet;
	}

	let { title, intro, children }: Props = $props();
</script>

<div class="flex min-h-dvh flex-wrap items-stretch">
	<section
		class="relative flex min-w-0 flex-[1_1_480px] flex-col gap-5 overflow-hidden bg-indigo px-6 pt-8 pb-12 text-white sm:px-13 sm:pt-11 sm:pb-14"
	>
		<Logo size="lg" inverted />
		<h1 class="mt-4 max-w-[14ch] text-4xl leading-[1.1] font-bold tracking-[-0.02em] sm:mt-6 sm:text-[46px]">
			{title}
		</h1>
		{@render intro?.()}
		<Baobab variant="panel" class="mt-auto hidden w-full max-w-[460px] md:block" />
		<Pagne height={12} deep class="absolute inset-x-0 bottom-0" />
	</section>

	<main class="flex min-w-0 flex-[1_1_480px] items-center justify-center px-4 py-10 sm:px-8">
		<div class="flex w-full max-w-[460px] flex-col gap-4.5 rounded-card bg-white px-6 py-8 sm:px-8.5 sm:py-9">
			{@render children()}
		</div>
	</main>
</div>
