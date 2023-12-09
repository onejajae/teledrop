<script>
	import { getFileInfo } from '$api/preview';

	export let password;
	export let isPasswordCorrect;
	export let key;
	export let promise;

	async function inputPassword() {
		console.log(5);
		promise = getFileInfo(key, password);
		isPasswordCorrect = false;
	}
</script>

<form on:submit|preventDefault={inputPassword}>
	<div class="text-center">
		<label for="password" class="form-label"><h3>비밀번호 입력</h3></label>
		<input
			type="password"
			id="password"
			class="form-control mb-3"
			class:is-invalid={!isPasswordCorrect}
			name="password"
			bind:value={password}
			autocomplete="off"
		/>
		<div class="invalid-feedback">비밀번호가 올바르지 않습니다.</div>
		<button type="submit" class="btn btn-primary">확인</button>
	</div>
</form>
