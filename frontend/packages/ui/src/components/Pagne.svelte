<!-- The band of wax print triangles under the header and at the bottom of the hero cards. -->
<script lang="ts">
	interface Props {
		height?: number;
		/** Darker ground, for the indigo panels. */
		deep?: boolean;
		class?: string;
	}

	let { height = 10, deep = false, class: className = '' }: Props = $props();
	const uid = $props.id();
	const id = `pagne-${uid}`;
	const width = $derived(height * 4);
</script>

<svg class="block w-full {className}" {height} aria-hidden="true">
	<defs>
		<pattern {id} {width} {height} patternUnits="userSpaceOnUse">
			<rect {width} {height} class={deep ? 'fill-indigo-deep' : 'fill-indigo'} />
			<polygon points="0,{height} {height},0 {height * 2},{height}" class="fill-sun" />
			<polygon points="{height * 2},{height} {height * 3},0 {width},{height}" class="fill-clay" />
			<rect y={height * 0.8} {width} height={height * 0.2} class="fill-leaf" />
		</pattern>
	</defs>
	<rect width="100%" {height} fill="url(#{id})" />
</svg>
