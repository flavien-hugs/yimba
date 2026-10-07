<!-- The figures of a conversation, only those its source provides: Facebook has no views, the press has none at all. -->
<script lang="ts">
	import type { Mention, Source } from '@yimba/api';
	import { Icon, formatCompact, formatNumber, type IconName } from '@yimba/ui';

	let { mention, class: className = '' }: { mention: Mention; class?: string } = $props();

	type Kind = 'likes' | 'shares' | 'views' | 'comments';
	const PROVIDED: Record<Source, Kind[]> = {
		facebook: ['likes', 'shares', 'comments'],
		instagram: ['likes', 'comments'],
		youtube: ['views', 'likes', 'comments'],
		bluesky: ['likes', 'shares', 'comments'],
		news: [],
		gdelt: []
	};
	const KINDS: Record<Kind, { icon: IconName; one: string; many: string }> = {
		likes: { icon: 'heart', one: "j'aime", many: "j'aime" },
		shares: { icon: 'share', one: 'partage', many: 'partages' },
		views: { icon: 'eye', one: 'vue', many: 'vues' },
		comments: { icon: 'comment', one: 'commentaire', many: 'commentaires' }
	};

	const figures = $derived(
		PROVIDED[mention.source].map((kind) => {
			const count = mention[kind];
			const name = count > 1 ? KINDS[kind].many : KINDS[kind].one;
			return {
				kind,
				icon: KINDS[kind].icon,
				count,
				text: formatCompact(count),
				label: `${formatNumber(count)} ${name}`
			};
		})
	);
</script>

{#if figures.length}
	<ul
		class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted tabular-nums {className}"
		aria-label="Réactions"
	>
		{#each figures as figure (figure.kind)}
			<li class="inline-flex items-center gap-1.5" title={figure.label}>
				<Icon name={figure.icon} size={16} />
				<span aria-hidden="true">{figure.text}</span>
				<span class="sr-only">{figure.label}</span>
			</li>
		{/each}
	</ul>
{/if}
