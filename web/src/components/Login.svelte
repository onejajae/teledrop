<script>
	import { Button, Heading, Label, Input, Helper } from 'flowbite-svelte';
	import Section from './Section.svelte';

	import { API } from '$lib/api.js';

	let incorrect = false;

	async function login(event) {
		const formData = new FormData(event.target);
		try {
			await API.login({ formData });
		} catch (error) {
			incorrect = true;
		}
	}
</script>

<Section>
	<div slot="content" class="p-6">
		<form class="flex flex-col space-y-5" on:submit|preventDefault={login}>
			<div class="text-center">
				<Heading tag="h4">로그인</Heading>
			</div>
			<Label class="space-y-3">
				<span>사용자 ID</span>
				<Input type="text" name="username" placeholder="사용자 ID" autoComplete="off" />
			</Label>
			<Label class="space-y-3">
				<span>비밀번호</span>
				<Input type="password" name="password" placeholder="••••••" autoComplete="off" />
			</Label>
			<Button type="submit">로그인</Button>
			{#if incorrect}
				<Helper class="text-center" color="red">
					<span class="font-medium">아이디 또는 비밀번호가 올바르지 않습니다.</span>
				</Helper>
			{/if}
		</form>
	</div>
</Section>
