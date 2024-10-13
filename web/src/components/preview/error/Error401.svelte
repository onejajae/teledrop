<script>
	import { Heading, Label, Input, Helper, Button, Modal } from 'flowbite-svelte';
	import Section from '../../Section.svelte';

	export let passwordCorrect = true;
	export let passwordResetModal = false;
	export let resetAvailable = false;
	export let handlePasswordSubmit;
	export let handlePasswordReset;

	let password1;
	let password2;
</script>

<Section>
	<div slot="content" class="flex justify-center text-center">
		<form on:submit|preventDefault={handlePasswordSubmit}>
			<Label>
				<Heading tag="h4">비밀번호 입력</Heading>
				<Input
					class="my-3 text-center"
					type="password"
					name="file-password"
					id="file-password"
					placeholder="••••••"
					color={!passwordCorrect ? 'red' : 'base'}
					autocomplete="off"
				/>
				{#if !passwordCorrect}
					<Helper class="my-3" color="red">
						<span class="font-medium">비밀번호가 올바르지 않습니다.</span>
					</Helper>
				{/if}
			</Label>
			<Button class="mb-1 px-8" type="submit" size="sm" outline pill>확인</Button>
		</form>
	</div>
	<div slot="footer" class="text-center">
		{#if resetAvailable && !passwordCorrect}
			<div class="mb-2">
				<button
					on:click={() => (passwordResetModal = !passwordResetModal)}
					class="rounded-lg p-1.5 px-2.5 font-light text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
				>
					비밀번호 초기화
				</button>
			</div>
		{/if}
	</div>
</Section>
<Modal title="비밀번호 초기화" size="xs" bind:open={passwordResetModal} outsideclose>
	<form on:submit|preventDefault={handlePasswordReset} class="flex flex-col space-y-4">
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
		<Button type="submit" disabled={!(password1 === password2 && Boolean(password1))}>수정</Button>
	</form>
</Modal>
