<script>
	import { login, refresh } from '$api/auth';
	let username;
	let password;
	let incorrect = false;
	async function loginHandle(event) {
		event.preventDefault();
		try {
			const response = await login(username, password);
			location.replace('/');
		} catch (error) {
			incorrect = true;
		}
	}
</script>

<div class="form-title text-center mb-3">
	<label for="username">
		<h4>로그인</h4>
	</label>
</div>

<div class="d-flex flex-column text-center">
	<form>
		<div class="form-group mb-3">
			<input
				type="text"
				class="form-control"
				id="username"
				placeholder="아이디"
				bind:value={username}
			/>
		</div>
		<div class="form-group mb-3">
			<input
				type="password"
				class="form-control"
				id="password"
				placeholder="비밀번호"
				bind:value={password}
			/>
		</div>
		{#if incorrect}
			<div class="form-text text-danger mb-3">아이디 또는 비밀번호가 올바르지 않습니다.</div>
		{/if}
		<button type="submit" class="btn btn-outline-primary rounded-pill" on:click={loginHandle}
			>확인</button
		>
	</form>
</div>
