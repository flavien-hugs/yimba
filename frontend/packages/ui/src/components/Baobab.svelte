<!-- A baobab under a large sun: the illustration of the home card and of the authentication panels. -->
<script lang="ts">
	interface Props {
		/** card: on white, compact: on white on a phone, panel: on the indigo panels. */
		variant?: 'card' | 'compact' | 'panel';
		class?: string;
	}

	let { variant = 'card', class: className = '' }: Props = $props();
</script>

{#if variant === 'card'}
	<svg viewBox="0 0 280 180" class="h-auto max-w-full {className}" aria-hidden="true">
		<circle cx="214" cy="56" r="58" fill="none" class="stroke-sun" stroke-width="2" opacity="0.35" />
		<circle cx="214" cy="56" r="46" fill="none" class="stroke-sun" stroke-width="3" opacity="0.55" />
		<circle cx="214" cy="56" r="34" class="fill-sun" />
		<path d="M0 158 Q70 148 140 156 T280 154 V180 H0Z" class="fill-indigo-soft" />
		<path d="M114 160 C119 134 124 114 121 94 L151 94 C148 114 153 134 160 160 Z" class="fill-bark" />
		<path
			d="M122 98 L96 72 M136 94 L136 62 M150 98 L178 70"
			class="stroke-bark"
			stroke-width="7"
			stroke-linecap="round"
		/>
		<ellipse cx="92" cy="62" rx="34" ry="20" class="fill-leaf-light" />
		<ellipse cx="136" cy="46" rx="42" ry="24" class="fill-leaf" />
		<ellipse cx="182" cy="60" rx="34" ry="20" class="fill-leaf-light" />
		<circle cx="52" cy="150" r="5" class="fill-clay" />
		<circle cx="238" cy="148" r="5" class="fill-indigo" />
	</svg>
{:else if variant === 'compact'}
	<svg viewBox="0 0 280 120" class="h-auto max-w-full {className}" aria-hidden="true">
		<circle cx="214" cy="40" r="42" fill="none" class="stroke-sun" stroke-width="2" opacity="0.4" />
		<circle cx="214" cy="40" r="30" class="fill-sun" />
		<path d="M0 108 Q70 100 140 106 T280 104 V120 H0Z" class="fill-indigo-soft" />
		<path d="M118 110 C122 94 126 84 124 70 L148 70 C146 84 150 94 156 110 Z" class="fill-bark" />
		<path
			d="M125 72 L104 54 M136 70 L136 46 M147 72 L168 52"
			class="stroke-bark"
			stroke-width="6"
			stroke-linecap="round"
		/>
		<ellipse cx="100" cy="46" rx="28" ry="16" class="fill-leaf-light" />
		<ellipse cx="136" cy="32" rx="34" ry="19" class="fill-leaf" />
		<ellipse cx="172" cy="44" rx="28" ry="16" class="fill-leaf-light" />
	</svg>
{:else}
	<svg viewBox="0 0 420 240" class="h-auto max-w-full {className}" aria-hidden="true">
		<circle cx="320" cy="76" r="88" fill="none" class="stroke-sun" stroke-width="2" opacity="0.35" />
		<circle cx="320" cy="76" r="70" fill="none" class="stroke-sun" stroke-width="3" opacity="0.55" />
		<circle cx="320" cy="76" r="52" class="fill-sun" />
		<path d="M0 214 Q110 200 210 210 T420 206 V240 H0Z" class="fill-indigo-hill" />
		<path d="M170 218 C178 180 186 154 182 124 L230 124 C226 154 232 180 244 218 Z" class="fill-bark" />
		<path
			d="M184 130 L146 94 M206 124 L206 80 M228 130 L268 90"
			class="stroke-bark"
			stroke-width="10"
			stroke-linecap="round"
		/>
		<ellipse cx="138" cy="84" rx="50" ry="29" class="fill-leaf-light" />
		<ellipse cx="206" cy="62" rx="62" ry="35" class="fill-leaf" />
		<ellipse cx="274" cy="82" rx="50" ry="29" class="fill-leaf-light" />
		<circle cx="70" cy="204" r="7" class="fill-clay" />
		<circle cx="360" cy="200" r="7" class="fill-sun" />
	</svg>
{/if}
