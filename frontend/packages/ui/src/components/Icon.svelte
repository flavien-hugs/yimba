<script lang="ts" module>
	export type IconName =
		| 'home'
		| 'chat'
		| 'bell'
		| 'plus'
		| 'search'
		| 'chevron'
		| 'warning'
		| 'external'
		| 'logout'
		| 'check'
		| 'person'
		| 'users'
		| 'back'
		| 'list'
		| 'heart'
		| 'share'
		| 'eye'
		| 'comment'
		| 'copy'
		| 'panel-collapse'
		| 'panel-expand';
</script>

<script lang="ts">
	interface Props {
		name: IconName;
		size?: number;
		class?: string;
	}

	let { name, size = 22, class: className = '' }: Props = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 22 22"
	fill="none"
	stroke="currentColor"
	stroke-width="1.8"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
	class="shrink-0 {className}"
>
	{#if name === 'home'}
		<rect x="3" y="3" width="7" height="9" rx="2" />
		<rect x="12" y="3" width="7" height="5" rx="2" />
		<rect x="12" y="10" width="7" height="9" rx="2" />
		<rect x="3" y="14" width="7" height="5" rx="2" />
	{:else if name === 'chat'}
		<path d="M4 5h14v9H9l-5 4V5Z" />
	{:else if name === 'bell'}
		<path d="M5 16V10a6 6 0 0 1 12 0v6l1.5 2h-15L5 16Z" />
		<path d="M9 20h4" />
	{:else if name === 'plus'}
		<circle cx="11" cy="11" r="8" />
		<path d="M11 7v8M7 11h8" />
	{:else if name === 'search'}
		<circle cx="9.5" cy="9.5" r="6" />
		<path d="m14 14 5 5" />
	{:else if name === 'chevron'}
		<path d="m6 9 5 5 5-5" />
	{:else if name === 'warning'}
		<path d="M11 3 20 19H2L11 3Z" />
		<path d="M11 9v4.5M11 16.5v.5" />
	{:else if name === 'external'}
		<path d="M13 4h5v5M18 4l-8 8M9 5H5v12h12v-4" />
	{:else if name === 'logout'}
		<path d="M9 4H5.5A1.5 1.5 0 0 0 4 5.5v11A1.5 1.5 0 0 0 5.5 18H9" />
		<path d="m14 7 4 4-4 4M18 11H9" />
	{:else if name === 'check'}
		<path d="m5 11.5 4 4 8-9" />
	{:else if name === 'person'}
		<circle cx="11" cy="8" r="3.6" fill="currentColor" stroke="none" />
		<path d="M4 19c1-4 4-5.5 7-5.5s6 1.5 7 5.5" fill="currentColor" stroke="none" />
	{:else if name === 'users'}
		<circle cx="8" cy="8" r="3" />
		<path d="M2.5 18c.8-3.2 3-4.5 5.5-4.5s4.7 1.3 5.5 4.5" />
		<path d="M14 5.2a3 3 0 0 1 0 5.6M16 13.8c1.6.6 2.9 1.9 3.5 4.2" />
	{:else if name === 'back'}
		<path d="M13 5 7 11l6 6" />
	{:else if name === 'list'}
		<path d="M8 6h10M8 11h10M8 16h10" />
		<circle cx="4.5" cy="6" r=".8" fill="currentColor" />
		<circle cx="4.5" cy="11" r=".8" fill="currentColor" />
		<circle cx="4.5" cy="16" r=".8" fill="currentColor" />
	{:else if name === 'heart'}
		<path d="M11 18.5S3.5 14 3.5 8.7A3.8 3.8 0 0 1 11 7a3.8 3.8 0 0 1 7.5 1.7C18.5 14 11 18.5 11 18.5Z" />
	{:else if name === 'share'}
		<path d="M4 12v4.5A1.5 1.5 0 0 0 5.5 18h11a1.5 1.5 0 0 0 1.5-1.5V12M11 14V4M7.5 7.5 11 4l3.5 3.5" />
	{:else if name === 'eye'}
		<path d="M2 11s3.2-6 9-6 9 6 9 6-3.2 6-9 6-9-6-9-6Z" />
		<circle cx="11" cy="11" r="2.6" />
	{:else if name === 'comment'}
		<path d="M4 5h14v9H9l-5 4V5Z" />
		<path d="M8 8.5h6M8 11h4" />
	{:else if name === 'copy'}
		<rect x="7" y="7" width="11" height="11" rx="2" />
		<path d="M4 14V6a2 2 0 0 1 2-2h8" />
	{:else if name === 'panel-collapse' || name === 'panel-expand'}
		<rect x="3" y="4" width="16" height="14" rx="2" />
		<path d="M8.5 4v14" />
		<path d={name === 'panel-collapse' ? 'm14.5 8.5-2.5 2.5 2.5 2.5' : 'm12 8.5 2.5 2.5-2.5 2.5'} />
	{/if}
</svg>
