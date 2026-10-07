<!-- Length is what makes a password strong (the API only checks the length): four segments, one sentence. -->
<script lang="ts">
	let { password, id }: { password: string; id?: string } = $props();

	const LEVELS = [
		{ text: '', bar: '' },
		{ text: 'Encore un peu court.', bar: 'bg-clay' },
		{ text: 'Correct. Une phrase plus longue le renforcerait.', bar: 'bg-gold' },
		{ text: 'Bien. Ajoutez un mot pour le renforcer.', bar: 'bg-leaf' },
		{ text: 'Excellent.', bar: 'bg-leaf' }
	];

	const length = $derived([...password].length);
	const level = $derived(length === 0 ? 0 : length < 10 ? 1 : length < 14 ? 2 : length < 20 ? 3 : 4);
</script>

<div class="flex flex-col gap-1.5" {id}>
	<div class="flex gap-1.5" aria-hidden="true">
		{#each [1, 2, 3, 4] as segment (segment)}
			<span class="h-2 flex-1 rounded {segment <= level ? LEVELS[level].bar : 'bg-track'}"></span>
		{/each}
	</div>
	<span class="text-sm text-muted" aria-live="polite">
		{LEVELS[level].text || 'Une phrase facile à retenir fonctionne très bien.'}
	</span>
</div>
