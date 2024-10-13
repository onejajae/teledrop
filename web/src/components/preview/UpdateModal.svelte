<script>
	import { Button, Modal, Label, Input, Textarea, Checkbox, Helper } from 'flowbite-svelte';

	export let open;
	export let post;
	export let handleUpdate;

	let usePassword = false;
	let deletePassword = false;
	let password1;
	let password2;
</script>

<Modal title="수정하기" size="sm" bind:open outsideclose>
	<form on:submit|preventDefault={handleUpdate} class="flex flex-col space-y-4">
		<Label class="space-y-2">
			<span>제목</span>
			<Input type="text" name="title" value={post.title} />
		</Label>
		<Label class="space-y-2">
			<span>내용</span>
			<Textarea name="description" rows="4" value={post.description} />
		</Label>
		<Checkbox name="is_user_only" checked={post.is_user_only}>사용자 전용</Checkbox>
		<div class="flex space-x-3">
			<Checkbox bind:checked={usePassword}>
				{#if post.required_password}
					비밀번호 수정
				{:else}
					비밀번호 사용
				{/if}
			</Checkbox>
			{#if usePassword && post.required_password}
				<Checkbox name="delete_password" bind:checked={deletePassword}>비밀번호 삭제</Checkbox>
			{/if}
		</div>

		{#if usePassword}
			<Label class="space-y-2">
				<span>새 비밀번호</span>
				<Input
					type="password"
					name="new_password"
					placeholder="•••••"
					color={password1 !== password2 ? 'red' : 'base'}
					autoComplete="off"
					bind:value={password1}
					disabled={deletePassword}
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
					disabled={deletePassword}
				/>
				{#if password1 !== password2}
					<Helper class="ms-1" color="red">
						<span class="font-medium">비밀번호가 일치하지 않습니다.</span>
					</Helper>
				{/if}
			</Label>
		{/if}
		<Button
			type="submit"
			disabled={!(
				!usePassword ||
				(usePassword && deletePassword) ||
				(usePassword && password1 === password2 && Boolean(password1))
			)}>수정</Button
		>
	</form>
</Modal>
