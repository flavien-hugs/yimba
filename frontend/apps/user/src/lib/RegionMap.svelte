<!-- The 14 districts of Côte d'Ivoire as a schematic grid (not a map): each tile shows its share of negative. -->
<script lang="ts">
	import type { Places } from '@yimba/api';
	import { formatNumber, percent } from '@yimba/ui';

	let { places }: { places: Places } = $props();

	// Position of each district in the grid of the design: [column, row].
	const LAYOUT: Record<string, [number, number]> = {
		Denguélé: [1, 1],
		Savanes: [3, 1],
		Zanzan: [5, 1],
		Woroba: [1, 2],
		'Vallée du Bandama': [3, 2],
		Montagnes: [1, 3],
		'Sassandra-Marahoué': [2, 3],
		Yamoussoukro: [3, 3],
		Lacs: [4, 3],
		Comoé: [5, 3],
		'Bas-Sassandra': [1, 4],
		'Gôh-Djiboua': [2, 4],
		Lagunes: [3, 4],
		Abidjan: [4, 4]
	};
	/** Below this, a share says nothing about a district. */
	const MIN = 3;

	const tiles = $derived(
		places.districts.map(({ district, counts }) => {
			const known = counts.total >= MIN;
			const pct = percent(counts.negative_share);
			const tone = !known
				? 'bg-lilac text-muted'
				: pct >= 50
					? 'bg-heat-max text-white'
					: pct >= 40
						? 'bg-heat-high text-heat-high-ink'
						: pct >= 30
							? 'bg-heat-mid text-heat-mid-ink'
							: 'bg-heat-low text-ink';
			const [col, row] = LAYOUT[district] ?? [1, 1];
			const label = known
				? `${district} : ${pct} % de négatif sur ${counts.total} conversations`
				: counts.total
					? `${district} : seulement ${counts.total} conversation${counts.total > 1 ? 's' : ''}, trop peu pour un chiffre`
					: `${district} : aucune conversation`;
			return { district, col, row, known, pct, tone, label };
		})
	);
</script>

<section class="card flex min-w-0 flex-[1_1_420px] flex-col gap-3.5" aria-labelledby="regions-title">
	<div>
		<h2 id="regions-title" class="mb-1 text-[22px] font-semibold">Dans quelles régions ça se tend</h2>
		<p class="text-sm text-muted">
			Part de paroles négatives dans les 14 districts. Disposition schématique, pas une carte.
		</p>
	</div>
	{#if places.located === 0}
		<p class="text-muted">
			Aucune conversation ne nomme encore un lieu : Yimba reconnaît les districts, les régions et les
			principales villes citées dans les textes.
		</p>
	{:else}
		<ul class="grid auto-rows-[76px] grid-cols-5 gap-1.5">
			{#each tiles as tile (tile.district)}
				<li
					class="flex min-w-0 flex-col justify-between overflow-hidden rounded-field px-2 py-2 {tile.tone}"
					style:grid-column={tile.col}
					style:grid-row={tile.row}
					title={tile.label}
				>
					<span class="text-[11px] leading-tight font-bold [overflow-wrap:anywhere] sm:text-xs"
						>{tile.district}</span
					>
					<span class="figure text-xl"
						>{tile.known ? `${tile.pct} %` : '—'}<span class="sr-only">. {tile.label}</span></span
					>
				</li>
			{/each}
		</ul>
		<div class="flex flex-wrap items-center gap-x-3.5 gap-y-2 text-[13px] text-muted">
			<span>Part de négatif :</span>
			<span class="inline-flex items-center gap-1.5"
				><span class="size-3.5 rounded bg-heat-low"></span>moins de 30 %</span
			>
			<span class="inline-flex items-center gap-1.5"
				><span class="size-3.5 rounded bg-heat-mid"></span>30 à 40 %</span
			>
			<span class="inline-flex items-center gap-1.5"
				><span class="size-3.5 rounded bg-heat-high"></span>40 à 50 %</span
			>
			<span class="inline-flex items-center gap-1.5"
				><span class="size-3.5 rounded bg-heat-max"></span>plus de 50 %</span
			>
		</div>
		<p class="text-[13px] text-muted">
			Calculé sur les {formatNumber(places.located)} conversations qui citent un lieu, sur {formatNumber(
				places.analyzed
			)} lues. Gris : moins de {MIN} conversations.
		</p>
	{/if}
</section>
