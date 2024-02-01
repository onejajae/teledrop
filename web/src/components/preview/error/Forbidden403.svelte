<script>
	import { Label, Input, Heading, Helper, Button } from 'flowbite-svelte';
	import { getFileInfo } from '$api/preview';

	export let password;
	export let isPasswordCorrect;
	export let key;
	export let promise;

	async function inputPassword() {
		promise = getFileInfo(key, password);
		isPasswordCorrect = false;
	}
</script>

<form on:submit|preventDefault={inputPassword}>
	<div class="grid justify-items-center">
		<Label for="file-password" class="mb-5"><Heading tag="h4">비밀번호 입력</Heading></Label>
		<Input
			class="w-full max-w-sm text-center"
			type="password"
			name="file-password"
			id="file-password"
			placeholder="••••••"
			bind:value={password}
			color={!isPasswordCorrect ? 'red' : 'base'}
			autocomplete="off"
		/>
		{#if !isPasswordCorrect}
			<Helper class="mt-2" color="red">
				<span class="font-medium">비밀번호가 올바르지 않습니다.</span>
			</Helper>
		{/if}

		<Button class="mt-5" color="green" outline pill type="submit">확인</Button>
	</div>
</form>
