<script>
	import { Listgroup, ListgroupItem, Tooltip, Select } from 'flowbite-svelte';
	import { RefreshOutline, LockSolid, LockOpenSolid, StarSolid } from 'flowbite-svelte-icons';
	import Section from './Section.svelte';
	import FileIcon from './FileIcon.svelte';

	import { API } from '$lib/api.js';
	import { postList, postPasswords, sortBy, orderBy } from '$lib/store.js';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	import { filesize } from 'filesize';
	import dayjs from 'dayjs';
	import 'dayjs/locale/ko';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import utc from 'dayjs/plugin/utc';
	dayjs.extend(relativeTime);
	dayjs.extend(utc);
	dayjs.locale('ko');

	const sortBys = [
		{ value: 'created_at', name: '날짜' },
		{ value: 'title', name: '제목' },
		{ value: 'file_size', name: '크기' }
	];

	async function reloadList() {
		try {
			await API.getPostList();
		} catch (error) {
			await API.logout();
		}
	}

	onMount(async () => {
		console.log();
		// try {
		// 	await API.getPostList();
		// } catch (error) {
		// 	await API.logout();
		// }
		await reloadList();
	});
</script>

<Section>
	<div slot="title" class="flex items-center space-x-1">
		<span>내 업로드</span>
		<button
			on:click={reloadList}
			class="rounded-lg p-1.5 text-xs text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
		>
			<RefreshOutline />
		</button>
		<Tooltip type="light">새로고침</Tooltip>
	</div>
	<div slot="control">
		<div class="flex items-center space-x-1">
			<span>
				<button
					on:click={async () => {
						orderBy.set($orderBy === 'desc' ? 'asc' : 'desc');
						await API.getPostList();
					}}
					class="rounded-lg p-1.5 px-2 font-semibold text-gray-600 hover:bg-gray-200 focus:outline-none dark:text-gray-100 dark:hover:bg-gray-500"
				>
					{#if $orderBy === 'desc'}
						내림차순
					{:else}
						오름차순
					{/if}
				</button>
			</span>
			<span>
				<Select
					class="font-semibold"
					items={sortBys}
					placeholder=""
					size="sm"
					bind:value={$sortBy}
					on:change={async () => await API.getPostList()}
				/>
			</span>
		</div>
	</div>
	<div slot="content">
		{#key $postList}
			<Listgroup active>
				{#each $postList as post}
					<ListgroupItem
						href="/{post.key}"
						current={post.key === $page.params.key}
						class="p-1 py-2"
					>
						<div class="flex items-center">
							<div class="p-1.5">
								<p class="text-xl"><FileIcon file_type={post.file_type} size="xl" /></p>
							</div>

							<div class="w-full min-w-0 flex-col ps-1">
								<div class="font-base flex items-center text-base">
									{#if post.favorite}
										<span class="pe-1"><StarSolid size="xs" /></span>
									{/if}
									<span class="truncate">
										{#if post.title}
											{post.title}
										{:else}
											{post.file_name}
										{/if}
									</span>
								</div>

								<div class="flex items-center space-x-1 truncate text-sm font-normal">
									<span>{filesize(post.file_size, { standard: 'jedec' })}</span>
									{#if !post.user_only}
										<span> • 전체 공개</span>
									{/if}
									<span> • {dayjs.utc(post.created_at).local().fromNow()}</span>
								</div>
							</div>
							{#if post.required_password}
								{#if $postPasswords[post.key]}
									<span class="pe-3"><LockOpenSolid size="sm" /> </span>
								{:else}
									<span class="pe-3"><LockSolid size="sm" /> </span>
								{/if}
							{/if}
						</div>
					</ListgroupItem>
				{/each}
			</Listgroup>
		{/key}
	</div>
	<!-- <div slot="footer" class="flex justify-center">
		<div class="mt-2 w-full max-w-52 space-y-1">
			<Progressbar
				size="h-1.5"
				class="bg-gray-300 dark:bg-gray-500"
				progress={Math.min(Math.floor(($usedCapacity / $maxCapacity) * 100), 100)}
			/>
			<P class="text-center text-sm font-semibold"
				>{filesize($usedCapacity, { standard: 'jedec' })} / {filesize($maxCapacity, {
					standard: 'jedec'
				})}</P
			>
		</div>
	</div> -->
</Section>
