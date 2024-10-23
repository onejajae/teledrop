<script>
	import { P, Button, Tooltip } from 'flowbite-svelte';
	import {
		DownloadOutline,
		TrashBinOutline,
		PenOutline,
		StarOutline,
		StarSolid
	} from 'flowbite-svelte-icons';

	import Section from '../Section.svelte';
	import Viewer from './Viewer.svelte';
	import FileInfo from './FileInfo.svelte';
	import Error401 from './error/Error401.svelte';
	import Error403 from './error/Error403.svelte';
	import Error404 from './error/Error404.svelte';
	import DeleteFinish from './DeleteFinish.svelte';
	import UpdateModal from './UpdateModal.svelte';

	import { postPasswords, username, accessToken, postList } from '$lib/store.js';
	import { API } from '$lib/api.js';
	import { onMount } from 'svelte';

	export let key;

	let postLoading = API.getPostPreview({ key, password: $postPasswords[key] });
	let passwordCorrect = true;
	let deleted = false;

	let updateModal = false;
	let passwordResetModal = false;

	async function handlePasswordSubmit(event) {
		const formData = new FormData(event.target);
		postLoading = API.getPostPreview({ key, password: formData.get('file-password') });
		passwordCorrect = false;
	}

	async function handlePasswordReset(event) {
		const formData = new FormData(event.target);
		await API.resetPostPassword({ key, formData });
		passwordResetModal = false;
		passwordCorrect = true;
	}

	async function handleDelete() {
		if (confirm('정말 삭제하시겠습니까?')) {
			await API.deletePost({ key, password: $postPasswords[key] });
			alert('삭제가 완료되었습니다.');
			deleted = true;
		}
	}

	async function handleUpdate(event) {
		const formData = new FormData(event.target);
		await API.updatePost({ key, password: $postPasswords[key], formData });
		postLoading = API.getPostPreview({ key });
		updateModal = false;
		passwordCorrect = true;
	}

	onMount(async () => {
		// detect token time out
		if ($accessToken) await API.getUserInfo();
	});
</script>

{#if !deleted}
	{#await postLoading then post}
		<Section>
			<span slot="title">
				{#if post.title}
					{post.title}
				{:else}
					미리보기
				{/if}
			</span>
			<div slot="control">
				{#if post.user.username === $username}
					<button
						on:click={async () => {
							await API.updatePostFavorite({
								key,
								password: $postPasswords[key],
								favorite: !post.favorite
							});
							post.favorite = !post.favorite;
						}}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
					>
						{#if post.favorite}
							<StarSolid />
							<Tooltip type="light">즐겨찾기 해제</Tooltip>
						{:else}
							<StarOutline />
							<Tooltip type="light">즐겨찾기 등록</Tooltip>
						{/if}
					</button>
					<button
						on:click={() => (updateModal = true)}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
					>
						<PenOutline />
					</button>
					<Tooltip type="light">수정</Tooltip>
					<button
						class="rounded-lg p-1.5 text-sm text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
						on:click={handleDelete}
					>
						<TrashBinOutline />
					</button>
					<Tooltip type="light">삭제</Tooltip>
				{/if}
			</div>
			<div slot="content" class="space-y-2">
				<div class="flex justify-center">
					<Viewer {post} />
				</div>

				{#if post.description}
					<div>
						<P class="mx-1" whitespace="prewrap">{post.description}</P>
					</div>
				{/if}

				<div>
					<FileInfo {post} />
				</div>
			</div>
			<div slot="footer">
				<div class="flex justify-center">
					<Button
						href={`${API.baseURL}/download/${key}?${$accessToken ? `access_token=${$accessToken}` : ''}${$postPasswords[key] ? `&password=${$postPasswords[key]}` : ''}`}
						size="sm"
						class="mx-2 px-5"
						pill
						outline
					>
						<DownloadOutline class="me-3" />다운로드
					</Button>
				</div>
			</div>
		</Section>
		<UpdateModal bind:open={updateModal} {post} {handleUpdate} />
	{:catch error}
		{#if error.response.status === 401}
			<Error401
				{handlePasswordReset}
				{handlePasswordSubmit}
				{passwordCorrect}
				bind:passwordResetModal
				resetAvailable={(function () {
					for (const post of $postList) {
						if (post.key === key) {
							return true;
						}
					}
					return false;
				})()}
			/>
		{:else if error.response.status === 403}
			<Error403 />
		{:else if error.response.status === 404}
			<Error404 />
		{/if}
	{/await}
{:else}
	<DeleteFinish />
{/if}
