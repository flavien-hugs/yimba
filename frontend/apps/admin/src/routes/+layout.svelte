<script lang="ts">
	import '../app.css';
	import '@yimba/ui/fonts';
	import favicon from '@yimba/ui/favicon.svg';
	import { goto } from '$app/navigation';
	import { navigating, page } from '$app/state';
	import { api } from '@yimba/api';
	import { ProgressBar } from '@yimba/ui';
	import { loginUrl } from '#lib/load.js';

	let { children } = $props();

	// The session ended outside a page load (refused by the API, logout in another tab): back to the login page.
	$effect(() =>
		api.onExpired(() => {
			if (!page.url.pathname.startsWith(loginUrl())) goto(loginUrl(page.url.pathname + page.url.search));
		})
	);
</script>

<svelte:head>
	<link rel="icon" href={favicon} type="image/svg+xml" />
</svelte:head>

<ProgressBar active={navigating.to !== null} />
{@render children()}
