<script>
	import { AccordionItem, Accordion } from 'flowbite-svelte';
	import {
		Label,
		Input,
		Textarea,
		InputAddon,
		ButtonGroup,
		Helper,
		Checkbox
	} from 'flowbite-svelte';
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
	<Accordion flush>
		<AccordionItem>
			<span slot="header" class="px-5">업로드 세부 설정</span>
			<div class="mb-3">
				<Label for="url-key" class="mb-2">접근 URL</Label>
				<ButtonGroup class="w-full">
					<InputAddon>https://onejajae.net/</InputAddon>
					<Input
						id="url-key"
						placeholder="입력하지 않으면 자동 생성됩니다."
						color={isKeyDuplicated ? 'red' : 'green'}
						on:change={keyCheck}
						bind:value={uploadDetail.key}
						autoComplete="off"
					/>
				</ButtonGroup>
				{#if isKeyDuplicated}
					<Helper class="" color="red">
						<span class="font-medium">이미 사용 중인 URL 입니다.</span>
					</Helper>
				{/if}
			</div>
			<div class="mb-3">
				<Label for="title" class="mb-2">제목</Label>
				<Input type="text" id="title" name="title" placeholder="제목" bind:value={uploadDetail.title} autoComplete="off"/>
			</div>
			<div class="mb-1">
				<Label for="description" class="mb-2">설명</Label>
				<Textarea
					id="description"
					placeholder=""
					rows="4"
					name="description"
					bind:value={uploadDetail.description}
				/>
			</div>
			<div class="mb-3">
				<Label for="password" class="mb-2">비밀번호</Label>
				<Input
					type="password"
					id="password"
					placeholder="•••••"
					bind:value={password1}
					on:input={passwordCheck}
					color={isPasswordValid ? 'base' : 'red'}
					autoComplete="new-password"
				/>
			</div>

			<div class="mb-3">
				<Label for="password-confirm" class="mb-2">비밀번호 확인</Label>
				<Input
					type="password"
					id="password-confirm"
					placeholder="•••••"
					bind:value={password2}
					on:input={passwordCheck}
					color={isPasswordValid ? 'base' : 'red'}
					autoComplete="new-password"
				/>
				{#if !isPasswordValid}
					<Helper class="" color="red">
						<span class="font-medium">비밀번호가 일치하지 않습니다.</span>
					</Helper>
				{/if}
			</div>

			<div class="mb-3">
				<Checkbox bind:checked={uploadDetail.user_only} disabled={isLogin}>사용자 전용</Checkbox>
			</div>
		</AccordionItem>
	</Accordion>
</form>
