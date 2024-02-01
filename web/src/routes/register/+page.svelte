<script>
	import { Button, Helper, Label, Input } from 'flowbite-svelte';

	import { refresh } from '$api/auth';
	import Loading from '$components/common/Loading.svelte';
	
	let username;
	let password1;
	let password2;
	let code;
	let isPasswordValid = true;
	let registerForm = {
		username: '',
		password: '',
		code: ''
	};
	async function registerHandle(event) {
		console.log(username, password1, password2, code);
	}
	async function passwordCheck() {
		if ((password1 === password2) === '') {
			isPasswordValid = true;
			return;
		}
		if (password1 !== password2) {
			isPasswordValid = false;
			return;
		} else {
			isPasswordValid = true;
			return;
		}
	}
</script>

<svelte:head>
	<title>회원가입</title>
</svelte:head>
{#await refresh()}
	<Loading></Loading>
{:then}
	<Loading></Loading>
	<script>
		location.replace('/');
	</script>
{:catch error}
	<div class="space-y-4 p-6 sm:p-8 md:space-y-6">
		<form on:submit|preventDefault={registerHandle} class="flex flex-col space-y-6">
			<h3 class="p-0 text-xl font-medium text-gray-900 dark:text-white">회원가입</h3>
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
					placeholder="•••••"
					bind:value={password1}
					on:input={passwordCheck}
					color={isPasswordValid ? 'base' : 'red'}
					autoComplete="off"
				/>
			</Label>
			<Label class="space-y-2">
				<span>비밀번호 확인</span>
				<Input
					type="password"
					name="confirm-password"
					placeholder="•••••"
					bind:value={password2}
					on:input={passwordCheck}
					color={isPasswordValid ? 'base' : 'red'}
					autoComplete="off"
				/>
				{#if !isPasswordValid}
					<Helper class="" color="red">
						<span class="font-medium">비밀번호가 일치하지 않습니다.</span>
					</Helper>
				{/if}
			</Label>
			<Label class="space-y-2">
				<span>승인 코드</span>
				<Input type="text" name="secret" bind:value={code} autoComplete="off" />
			</Label>
			<Button type="submit" class="w-full1">Create an account</Button>
			<div class="text-sm font-medium text-gray-500 dark:text-gray-300">
				이미 계정이 있다면 <a
					href="/login"
					class="font-medium text-primary-600 hover:underline dark:text-primary-500"
					>클릭하여 로그인</a
				>
			</div>
		</form>
	</div>
{/await}
