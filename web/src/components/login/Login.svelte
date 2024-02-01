<script>
	import { Button, Heading, Label, Input, Helper, Spinner } from 'flowbite-svelte';
	import { login, refresh } from '$api/auth';
	let username;
	let password;
	let incorrect = false;
	let waitLogin = false;
	async function loginHandle(event) {
		waitLogin = true;
		event.preventDefault();
		try {
			const response = await login(username, password);
			location.replace('/');
		} catch (error) {
			incorrect = true;
			waitLogin = false;
		}
		waitLogin = false;
	}
</script>

<div class="mb-4 space-y-4 p-5">
	<form class="flex flex-col space-y-6" action="/">
		<div class="text-center">
			<Heading tag="h4">로그인</Heading>
		</div>
		<Label class="space-y-2">
			<span>사용자 ID</span>
			<Input
				type="text"
				name="username"
				placeholder="사용자 ID"
				bind:value={username}
				autoComplete="off"
			/>
		</Label>
		<Label class="space-y-2">
			<span>비밀번호</span>
			<Input
				type="password"
				name="password"
				placeholder="••••••"
				bind:value={password}
				autoComplete="off"
			/>
		</Label>
		<Button type="submit" on:click={loginHandle}>
			{#if waitLogin}
				<Spinner size="4" />
			{:else}
				로그인
			{/if}
		</Button>
		{#if incorrect}
			<Helper class="mt-2" color="red">
				<span class="font-medium">아이디 또는 비밀번호가 올바르지 않습니다.</span>
			</Helper>
		{/if}
	</form>
</div>
