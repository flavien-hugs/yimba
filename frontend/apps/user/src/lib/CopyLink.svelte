<!-- Copies an address to the clipboard and says so for a moment. -->
<script lang="ts">
	import { Icon } from '@yimba/ui';

	let { url, class: className = '' }: { url: string; class?: string } = $props();

	let state = $state<'idle' | 'copied' | 'failed'>('idle');
	let timer: ReturnType<typeof setTimeout> | undefined;

	/** The old way, for pages without the clipboard API or when it is refused. */
	function copyWithSelection(): boolean {
		const field = document.createElement('textarea');
		field.value = url;
		field.setAttribute('readonly', '');
		field.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
		document.body.append(field);
		field.select();
		try {
			return document.execCommand('copy');
		} catch {
			return false;
		} finally {
			field.remove();
		}
	}

	async function copy() {
		let done = false;
		try {
			await navigator.clipboard.writeText(url);
			done = true;
		} catch {
			done = copyWithSelection();
		}
		state = done ? 'copied' : 'failed';
		clearTimeout(timer);
		timer = setTimeout(() => (state = 'idle'), 2500);
	}
</script>

<button type="button" class="btn btn-ghost min-h-11 px-4 text-sm {className}" onclick={copy}>
	<Icon name={state === 'copied' ? 'check' : 'copy'} size={16} />
	{state === 'copied' ? 'Lien copié' : state === 'failed' ? 'Copie impossible' : 'Copier le lien'}
</button>
<span class="sr-only" role="status">{state === 'copied' ? 'Lien copié' : ''}</span>
