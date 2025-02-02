<script>
	import { Button, Modal, Label, Input, Helper } from 'flowbite-svelte';

	export let open;
	export let handleUpdatePassword;

	let password1;
	let password2;
</script>

<Modal title="비밀번호 설정" size="sm" bind:open outsideclose>
	<form on:submit|preventDefault={handleUpdatePassword} class="flex flex-col space-y-4">
		<Label class="space-y-2">
			<span>새 비밀번호</span>
			<Input
				type="password"
				name="new_password"
				placeholder="•••••"
				color={password1 !== password2 ? 'red' : 'base'}
				autoComplete="off"
				bind:value={password1}
			/>
		</Label>
		<Label class="space-y-2">
			<span>비밀번호 확인</span>
			<Input
				type="password"
				placeholder={password1 ? '' : '•••••'}
				color={password1 !== password2 ? 'red' : 'base'}
				autoComplete="off"
				bind:value={password2}
			/>
			{#if password1 !== password2}
				<Helper class="ms-1" color="red">
					<span class="font-medium">비밀번호가 일치하지 않습니다.</span>
				</Helper>
			{/if}
		</Label>
		<Button type="submit" disabled={!(password1 === password2 && Boolean(password1))}
			>비밀번호 설정</Button
		>
	</form>
</Modal>
