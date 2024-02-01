<script>
	import { Dropzone } from 'flowbite-svelte';
	export let file;
	let value = [];
	let filename = '';
	const dropHandle = (event) => {
		value = [];
		event.preventDefault();

		if (event.dataTransfer.items) {
			const file = event.dataTransfer.items[0].getAsFile();
			filename = file.name;
			[...event.dataTransfer.items].forEach((item, i) => {
				console.log(item);
				if (!item.type) {
					alert('폴더를 업로드할 수 없습니다.');
					filename = '';
				}
			});
		} else {
			filename = event.dataTransfer.files[0].name;
		}
	};

	const handleChange = (event) => {
		if (!file[0].type) {
			alert('폴더를 업로드할 수 없습니다.');
			filename = '';
			return;
		}
		const files = event.target.files;
		filename = files[0].name;
		// if (files.length > 0) {
		// 	value.push(files[0].name);
		// 	value = value;
		// }
	};

	// const showFiles = (files) => {
	// 	if (files.length === 1) return files[0];
	// 	let concat = '';
	// 	files.map((file) => {
	// 		concat += file;
	// 		concat += ',';
	// 		concat += ' ';
	// 	});

	// 	if (concat.length > 40) concat = concat.slice(0, 40);
	// 	concat += '...';
	// 	return concat;
	// };
</script>

<Dropzone
	id="dropzone"
	on:drop={dropHandle}
	on:dragover={(event) => {
		event.preventDefault();
	}}
	on:change={handleChange}
	bind:files={file}
>
	{#if !filename}
		<svg
			aria-hidden="true"
			class="mb-3 h-10 w-10 text-gray-400"
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
		<p class="mb-2 text-sm text-gray-500 dark:text-gray-400">
			<span class="font-semibold">클릭하여 업로드</span> 또는 끌어서 가져오기
		</p>
	{:else}
		<!-- <p>{showFiles(value)}</p> -->
		<p>{filename}</p>
	{/if}
</Dropzone>
