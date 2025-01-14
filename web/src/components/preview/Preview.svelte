<script>
	import { P, Button, Tooltip } from 'flowbite-svelte';
	import {
		DownloadOutline,
		TrashBinOutline,
		PenOutline,
		StarOutline,
		LockSolid,
		LockOpenSolid,
		StarSolid,
		UserCircleSolid,
		GlobeSolid
	} from 'flowbite-svelte-icons';

	import Section from '../Section.svelte';
	import Viewer from './Viewer.svelte';
	import FileInfo from './FileInfo.svelte';
	import Error401 from './error/Error401.svelte';
	import Error403 from './error/Error403.svelte';
	import Error404 from './error/Error404.svelte';
	import DeleteFinish from './DeleteFinish.svelte';
	import UpdatDetailModal from './UpdateDetailModal.svelte';
	import UpdatePasswordModal from './UpdatePasswordModal.svelte';

	import { postPasswords, accessToken, postList } from '$lib/store.js';
	import { API } from '$lib/api.js';
	import { onMount } from 'svelte';

	export let key;

	let postLoading = API.getPostPreview({ key, password: $postPasswords[key] });
	let passwordCorrect = true;
	let deleted = false;

	let updateDetailModal = false;
	let updatePasswordModal = false;

	async function handlePasswordSubmit(event) {
		const formData = new FormData(event.target);
		postLoading = API.getPostPreview({ key, password: formData.get('file-password') });
		passwordCorrect = false;
	}

	async function handleDelete() {
		if (confirm('정말 삭제하시겠습니까?')) {
			await API.deletePost({ key, password: $postPasswords[key] });
			alert('삭제가 완료되었습니다.');
			deleted = true;
		}
	}

	async function handleUpdatePassword(event) {
		const formData = new FormData(event.target);
		await API.updatePostPassword({ key, formData });
		postLoading = API.getPostPreview({ key, password: $postPasswords[key] });
		updatePasswordModal = false;
		passwordCorrect = true;
	}

	async function handleUpdateDetail(event) {
		const formData = new FormData(event.target);
		await API.updatePostDetail({ key, password: $postPasswords[key], formData });
		postLoading = API.getPostPreview({ key, password: $postPasswords[key] });
		updateDetailModal = false;
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
				{#if $accessToken}
					<button
						on:click={async () => {
							await API.updatePostPermission({
								key,
								password: $postPasswords[key],
								user_only: !post.user_only
							});
							post.user_only = !post.user_only;
						}}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
					>
						{#if post.user_only}
							<UserCircleSolid />
						{:else}
							<GlobeSolid />
						{/if}
					</button>
					{#if post.user_only}
						<Tooltip type="light">전체 보기로 변경</Tooltip>
					{:else}
						<Tooltip type="light">나만 보기로 변경</Tooltip>
					{/if}
					{#if post.required_password}
						<button
							on:click={async () => {
								if (confirm('비밀번호 설정을 해제하시겠습니까?')) {
									await API.resetPostPassword({ key, password: $postPasswords[key] });
									alert('비밀번호가 해제되었습니다.');
								}
								post.required_password = false;
							}}
							class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
						>
							<LockSolid />
						</button>
						<Tooltip type="light">비밀번호 해제</Tooltip>
					{:else}
						<button
							on:click={async () => {
								updatePasswordModal = true;
							}}
							class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
						>
							<LockOpenSolid />
						</button>
						<Tooltip type="light">비밀번호 등록</Tooltip>
					{/if}

					<button
						on:click={async () => {
							await API.updatePostFavorite({
								key,
								password: $postPasswords[key],
								favorite: !post.favorite
							});
							post.favorite = !post.favorite;
						}}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 hover:text-amber-300 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500 dark:hover:text-yellow-300"
					>
						{#if post.favorite}
							<StarSolid />
						{:else}
							<StarOutline />
						{/if}
					</button>
					{#if post.favorite}
						<Tooltip type="light">즐겨찾기 해제</Tooltip>
					{:else}
						<Tooltip type="light">즐겨찾기 설정</Tooltip>
					{/if}
					<button
						on:click={() => (updateDetailModal = true)}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
					>
						<PenOutline />
					</button>
					<Tooltip type="light">수정</Tooltip>
					<button
						class="rounded-lg p-1.5 text-sm text-gray-600 hover:bg-gray-200 hover:text-red-500 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500 dark:hover:text-rose-500"
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
				<div class="mb-1 flex justify-center">
					<Button
						href={`${API.baseURL}/download/${key}?${$accessToken ? `access_token=${$accessToken}` : ''}${$postPasswords[key] ? `&password=${$postPasswords[key]}` : ''}`}
						size="sm"
						class="mx-2 px-5"
						color="light"
					>
						<DownloadOutline class="me-3" />다운로드
					</Button>
				</div>
			</div>
		</Section>
		<UpdatDetailModal bind:open={updateDetailModal} {post} {handleUpdateDetail} />
		<UpdatePasswordModal bind:open={updatePasswordModal} {handleUpdatePassword} />
	{:catch error}
		{#if error.response.status === 401}
			<Error401
				{handleUpdatePassword}
				{handlePasswordSubmit}
				{passwordCorrect}
				bind:updatePasswordModal
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
