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

	import { dropPasswords, dropList, isLogin } from '$lib/store.js';
	import { API, API_BASE_URL } from '$lib/api.js';
	import { onMount } from 'svelte';

	export let slug;

	let dropLoading = API.getDropPreview({ slug, password: $dropPasswords[slug] });
	let passwordCorrect = true;
	let deleted = false;

	let updateDetailModal = false;
	let updatePasswordModal = false;

	async function handlePasswordSubmit(event) {
		const formData = new FormData(event.target);
		dropLoading = API.getDropPreview({ slug, password: formData.get('file-password') });
		passwordCorrect = false;
	}

	async function handleDelete() {
		if (confirm('정말 삭제하시겠습니까?')) {
			await API.deleteDrop({ slug, password: $dropPasswords[slug] });
			alert('삭제가 완료되었습니다.');
			deleted = true;
		}
	}

	async function handleUpdatePassword(event) {
		const formData = new FormData(event.target);
		await API.updateDropPassword({ slug, formData });
		dropLoading = API.getDropPreview({ slug, password: $dropPasswords[slug] });
		updatePasswordModal = false;
		passwordCorrect = true;
	}

	async function handleUpdateDetail(event) {
		const formData = new FormData(event.target);
		await API.updateDropDetail({ slug, password: $dropPasswords[slug], formData });
		dropLoading = API.getDropPreview({ slug, password: $dropPasswords[slug] });
		updateDetailModal = false;
		passwordCorrect = true;
	}

	onMount(async () => {
		// detect token time out
		if ($isLogin) {
			try {
				await API.getUserInfo();
			} catch (error) {
				await API.logout();
			}
		}
	});
</script>

{#if !deleted}
	{#await dropLoading then drop}
		<Section>
			<span slot="title">
				{#if drop.title}
					{drop.title}
				{:else}
					미리보기
				{/if}
			</span>
			<div slot="control">
				{#if $isLogin}
					<button
						on:click={async () => {
							await API.updateDropPermission({
								slug,
								password: $dropPasswords[slug],
								is_private: !drop.is_private
							});
							drop.is_private = !drop.is_private;
						}}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
					>
						{#if drop.is_private}
							<UserCircleSolid />
						{:else}
							<GlobeSolid />
						{/if}
					</button>
					{#if drop.is_private}
						<Tooltip type="light">전체 보기로 변경</Tooltip>
					{:else}
						<Tooltip type="light">나만 보기로 변경</Tooltip>
					{/if}
					{#if drop.has_password}
						<button
							on:click={async () => {
								if (confirm('비밀번호 설정을 해제하시겠습니까?')) {
									await API.resetDropPassword({ slug, password: $dropPasswords[slug] });
									alert('비밀번호가 해제되었습니다.');
									drop.has_password = false;
								}
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
							await API.updateDropFavorite({
								slug,
								password: $dropPasswords[slug],
								is_favorite: !drop.is_favorite
							});
							drop.is_favorite = !drop.is_favorite;
						}}
						class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 hover:text-amber-300 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500 dark:hover:text-yellow-300"
					>
						{#if drop.is_favorite}
							<StarSolid />
						{:else}
							<StarOutline />
						{/if}
					</button>
					{#if drop.is_favorite}
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
					<Viewer drop={drop} />
				</div>

				{#if drop.description}
					<div>
						<P class="mx-1" whitespace="prewrap">{drop.description}</P>
					</div>
				{/if}

				<div>
					<FileInfo drop={drop} />
				</div>
			</div>
			<div slot="footer">
				<div class="mb-1 flex justify-center">
					<Button
						rel="external"
						href={`${API_BASE_URL}/drop/${slug}${$dropPasswords[slug] ? `?password=${$dropPasswords[slug]}` : ''}`}
						size="sm"
						class="mx-2 px-5"
						color="light"
					>
						<DownloadOutline class="me-3" />다운로드
					</Button>
				</div>
			</div>
		</Section>
		<UpdatDetailModal bind:open={updateDetailModal} drop={drop} {handleUpdateDetail} />
		<UpdatePasswordModal bind:open={updatePasswordModal} {handleUpdatePassword} />
	{:catch error}
		{#if error.response.status === 401}
			<Error401
				{handleUpdatePassword}
				{handlePasswordSubmit}
				{passwordCorrect}
				bind:updatePasswordModal
				resetAvailable={(function () {
					for (const drop of $dropList) {
						if (drop.slug === slug) {
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
