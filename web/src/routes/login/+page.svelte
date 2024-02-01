<script>
	import { refresh } from '$api/auth';
	import Loading from '$components/common/Loading.svelte';
	import Login from '$components/login/Login.svelte';
	let username;
	let password;
	let incorrect = false;
</script>

<svelte:head>
	<title>로그인</title>
</svelte:head>
{#await refresh()}
	<Loading></Loading>
{:then data}
	{#if data.access_token}
		<Loading></Loading>
		<script>
			location.replace('/');
		</script>
	{:else}
		<Login bind:username bind:password bind:incorrect></Login>
	{/if}
{:catch}
	<Login bind:username bind:password bind:incorrect></Login>
{/await}
