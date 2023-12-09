<script>
	import { isKeyExist } from '$api/upload';
	export let uploadDetail = {
		key: '',
		title: '',
		description: '',
		password: '',
		is_anonymous: true,
		user_only: false
	};
	export let isKeyDuplicated = false;
	export let isPasswordValid = true;
	export let isLogin;

	let password1;
	let password2;

	async function keyCheck() {
		if (uploadDetail.key) {
			const res = await isKeyExist(uploadDetail.key);
			isKeyDuplicated = res.exist;
		} else {
			isKeyDuplicated = false;
		}
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
			uploadDetail.password = password1;
			return;
		}
	}
</script>

<form>
	<div class="accordion accordion-flush" id="upload-accordion">
		<div class="accordion-item">
			<h5 class="accordion-header">
				<button
					class="accordion-button collapsed"
					type="button"
					data-bs-toggle="collapse"
					data-bs-target="#upload-configs"
					aria-expanded="false"
					aria-controls="upload-configs"
				>
					업로드 세부 설정
				</button>
			</h5>

			<div
				id="upload-configs"
				class="accordion-collapse collapse"
				data-bs-parent="#upload-accordion"
			>
				<div class="accordion-body">
					<div class="mb-3">
						<label for="url-key" class="form-label">접근 URL</label>
						<div class="input-group">
							<span class="input-group-text" id="keyInput">https://onejajae.net/</span>
							<input
								type="text"
								class="form-control"
								id="url-key"
								aria-describedby="keyInput basic-addon4"
								bind:value={uploadDetail.key}
								autocomplete="off"
								class:is-valid={!isKeyDuplicated}
								class:is-invalid={isKeyDuplicated}
								on:change={keyCheck}
								placeholder="입력하지 않으면 자동 생성됩니다."
							/>
							<div id="url-key-feedback" class="invalid-feedback">이미 사용 중인 URL 입니다.</div>
						</div>
					</div>
					<div class="mb-3">
						<label for="titleInput" class="form-label">제목</label>
						<input
							type="text"
							class="form-control"
							id="titleInput"
							bind:value={uploadDetail.title}
							autocomplete="off"
						/>
					</div>
					<div class="mb-3">
						<label for="descriptionInput" class="form-label">설명</label>
						<textarea
							class="form-control"
							id="descriptionInput"
							rows="3"
							bind:value={uploadDetail.description}
						></textarea>
					</div>
					<div class="mb-3">
						<label for="passwordInput1" class="form-label">비밀번호</label>
						<input
							type="password"
							class="form-control"
							class:is-invalid={!isPasswordValid}
							id="passwordInput1"
							bind:value={password1}
							autocomplete="off"
							on:input={passwordCheck}
						/>
					</div>
					<div class="mb-3">
						<label for="passwordInput2" class="form-label">비밀번호 확인</label>
						<input
							type="password"
							class="form-control"
							class:is-invalid={!isPasswordValid}
							id="passwordInput2"
							bind:value={password2}
							autocomplete="off"
							on:input={passwordCheck}
						/>
						<div id="url-key-feedback" class="invalid-feedback">비밀번호가 일치하지 않습니다.</div>
					</div>
					<div class="mb-3">
						<div class="row">
							<div class="col">
								<div class="form-check">
									<input
										class="form-check-input"
										type="checkbox"
										id="flexCheckDefault"
										disabled={!isLogin}
										bind:checked={uploadDetail.is_anonymous}
									/>
									<label class="form-check-label" for="flexCheckDefault"> 익명으로 업로드 </label>
								</div>
							</div>
							<div class="col">
								<div class="form-check">
									<input
										class="form-check-input"
										type="checkbox"
										id="flexCheckChecked"
										disabled={isLogin && uploadDetail.is_anonymous}
										bind:checked={uploadDetail.user_only}
									/>
									<label class="form-check-label" for="flexCheckChecked"> 사용자 전용 </label>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</form>
