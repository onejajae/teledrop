<script>
	import {
		Dropzone,
		Label,
		Input,
		Helper,
		Checkbox,
		Button,
		AccordionItem,
		Accordion,
		Textarea,
		P,
		Img
	} from 'flowbite-svelte';
	import { FileOutline } from 'flowbite-svelte-icons';
	import { UploadOutline } from 'flowbite-svelte-icons';
	import { API } from '$lib/api.js';

	export let file;
	export let handleUpload;

	let files;
	let key;
	let password1;
	let password2;

	let isKeyExist = false;
	let usePassword = false;

	let filename;
	let filetype;
	let filedata;

	function handleFileDrop(event) {
		event.preventDefault();
		for (let tempFile of event.dataTransfer.files) {
			if (!tempFile.type) {
				alert('폴더를 업로드할 수 없습니다.');
				filename = '';
				file = null;
				break;
			}
			file = tempFile;
			filename = tempFile.name;
			filetype = tempFile.type;
			URL.revokeObjectURL(filedata);
			filedata = URL.createObjectURL(tempFile);
		}
	}

	function handleFileChange(event) {
		if (!files[0].type) {
			alert('폴더를 업로드할 수 없습니다.');
			filename = '';
			file = null;
			return;
		}
		file = files[0];
		filename = files[0].name;
		filetype = event.target.files[0].type;
		URL.revokeObjectURL(filedata);
		filedata = URL.createObjectURL(files[0]);
	}

	async function handleKeyChange(event) {
		if (key) {
			isKeyExist = await API.getKeyExist({ key });
		} else {
			isKeyExist = false;
		}
	}
</script>

<form on:submit|preventDefault={handleUpload} class="flex flex-col space-y-3">
	<Dropzone
		class="h-full p-3"
		id="dropzone"
		name="file"
		on:drop={handleFileDrop}
		on:dragover={(event) => {
			event.preventDefault();
		}}
		on:change={handleFileChange}
		bind:files
	>
		{#if !filename}
			<div class="my-10 flex flex-col items-center space-y-3">
				<p class="text-center">
					<svg
						aria-hidden="true"
						class="h-10 w-10 text-gray-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						xmlns="http://www.w3.org/2000/svg"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
						/></svg
					>
				</p>

				<p class=" text-gray-500 dark:text-gray-400">
					<span class="font-semibold">클릭하여 업로드</span> 또는 끌어서 가져오기
				</p>
			</div>
		{:else}
			{#key filedata}
				<div>
					{#if filetype.startsWith('image/')}
						<Img class="max-h-svh" src={filedata} />
					{:else if filetype.startsWith('video/')}
						<video class="max-h-svh" controls>
							<source src={filedata} type={filetype} />
							<track kind="captions" />
							이 브라우저에서는 미리보기가 지원되지 않습니다.
						</video>
					{:else}
						<P><FileOutline class="size-20"></FileOutline></P>
					{/if}
				</div>
				<p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
					<span class="font-semibold">{filename}</span>
				</p>
			{/key}
		{/if}
	</Dropzone>

	<Label for="url-key" class="space-y-1">
		<span>접근 URL</span>
		<div class="flex">
			<Button class="rounded-e-none px-3" color="light" disabled
				>{import.meta.env.VITE_API_HOST}/</Button
			>
			<Input
				clearable
				type="text"
				name="key"
				id="url-key"
				class="rounded-s-none"
				color={isKeyExist ? 'red' : 'green'}
				placeholder="입력하지 않으면 자동 생성됩니다."
				autoComplete="off"
				on:change={handleKeyChange}
				bind:value={key}
			></Input>
		</div>
		{#if isKeyExist}
			<Helper class="text-center" color="red">
				<span class="font-medium">이미 사용 중인 URL 입니다.</span>
			</Helper>
		{/if}
	</Label>

	<Checkbox name="user_only" checked>나만 보기</Checkbox>
	<Checkbox bind:checked={usePassword}>비밀번호 사용</Checkbox>

	{#if usePassword}
		<div class="space-y-2">
			<Label class="space-y-2">
				<span>비밀번호</span>
				<Input
					type="password"
					name="password"
					placeholder="•••••"
					color={password1 !== password2 ? 'red' : 'base'}
					autoComplete="new-password"
					bind:value={password1}
				/>
			</Label>
			<Label class="space-y-2">
				<span>비밀번호 확인 </span>
				<Input
					type="password"
					placeholder={password1 ? '' : '•••••'}
					color={password1 !== password2 ? 'red' : 'base'}
					autoComplete="new-password"
					bind:value={password2}
				/></Label
			>
			{#if password1 !== password2}
				<Helper class="ms-1 mt-1" color="red">
					<span class="font-medium">비밀번호가 일치하지 않습니다.</span>
				</Helper>
			{/if}
		</div>
	{/if}

	<Accordion flush>
		<AccordionItem paddingFlush="pt-1">
			<P slot="header">추가 정보 입력</P>
			<div class="space-y-3 pt-2">
				<Label class="space-y-2">
					<span>제목</span>
					<Input type="text" name="title" placeholder="제목" autoComplete="off" />
				</Label>
				<Label class="space-y-2">
					<span>내용</span>
					<Textarea name="description" rows="4" />
				</Label>
			</div>
		</AccordionItem>
	</Accordion>

	<div class="mb-2 mt-5 text-center">
		<Button
			class="my-1 px-8"
			size="sm"
			color="green"
			outline
			type="submit"
			disabled={!(
				Boolean(file) &&
				!isKeyExist &&
				(!usePassword || (password1 === password2 && Boolean(password1)))
			)}><UploadOutline class="me-3" />업로드</Button
		>
	</div>
</form>
