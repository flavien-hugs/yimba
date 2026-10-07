<!-- One bar split into negative, neutral and positive, in that order. -->
<script lang="ts">
	interface Props {
		negative: number;
		neutral: number;
		positive: number;
		class?: string;
	}

	let { negative, neutral, positive, class: className = '' }: Props = $props();
	const total = $derived(negative + neutral + positive || 1);
	const width = (count: number) => `${(count / total) * 100}%`;
</script>

<div class="flex h-3 overflow-hidden rounded-md bg-track {className}" aria-hidden="true">
	<div class="bg-clay" style:width={width(negative)}></div>
	<div class="bg-sand" style:width={width(neutral)}></div>
	<div class="bg-leaf" style:width={width(positive)}></div>
</div>
