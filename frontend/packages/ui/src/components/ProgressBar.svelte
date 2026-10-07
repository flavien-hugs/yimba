<!-- A thin bar at the top of the window while a page loads its data. -->
<script lang="ts">
	let { active }: { active: boolean } = $props();
</script>

{#if active}
	<div
		class="fixed inset-x-0 top-0 z-50 h-1 overflow-hidden bg-indigo-soft"
		role="progressbar"
		aria-label="Chargement"
	>
		<div class="h-full w-1/3 animate-progress bg-sun motion-reduce:w-full motion-reduce:animate-none"></div>
	</div>
{/if}
