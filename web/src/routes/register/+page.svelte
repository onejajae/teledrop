<script>
	import { refresh } from '$api/auth';
	import Loading from '$components/common/Loading.svelte';
	let username;
	let password1;
	let password2;
	let isPasswordValid = true;
	let registerForm = {
		username: '',
		password: '',
		code: ''
	};
	async function registerHandle(event) {}
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

{#await refresh()}
	<Loading></Loading>
{:then}
	<Loading></Loading>
	<script>
		location.replace('/');
	</script>
{:catch error}
	<h2>회원가입</h2>
	<form>
		<div class="mb-4">
			<label for="inputUsername" class="form-label">계정 이름</label>
			<input id="inputUsername" type="text" class="form-control" bind:value={username} />
		</div>

		<div class="mb-4">
			<label for="inputPassword1" class="form-label">비밀번호</label>
			<input
				id="inputPassword1"
				type="password"
				class="form-control"
				bind:value={password1}
				on:input={passwordCheck}
				class:is-invalid={!isPasswordValid}
			/>
		</div>
		<div class="mb-4">
			<label for="inputPassword2" class="form-label">비밀번호 확인</label>
			<input
				id="inputPassword2"
				type="password"
				class="form-control"
				bind:value={password2}
				on:input={passwordCheck}
				class:is-invalid={!isPasswordValid}
			/>
			<div id="url-key-feedback" class="invalid-feedback">비밀번호가 일치하지 않습니다.</div>
		</div>

		<div class="mb-4">
			<label for="inputPassword2" class="form-label">승인 코드</label>
			<input id="inputPassword2" type="text" class="form-control" />
		</div>
		<button type="submit" class="btn btn-outline-primary rounded-pill" on:click={registerHandle}
			>확인</button
		>
	</form>
{/await}
