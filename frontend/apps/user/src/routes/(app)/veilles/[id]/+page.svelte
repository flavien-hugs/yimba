<script lang="ts">
	import WatchForm from '#lib/WatchForm.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.watch.name} · Yimba</title>
</svelte:head>

{#key data.watch.id}
	<WatchForm watch={data.watch} />
{/key}
