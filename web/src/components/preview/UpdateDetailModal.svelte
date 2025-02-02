<script>
	import { Button, Modal, Label, Input, Textarea } from 'flowbite-svelte';

	export let open;
	export let post;
	export let handleUpdateDetail;
</script>

<Modal title="수정하기" size="sm" bind:open outsideclose>
	<form on:submit|preventDefault={handleUpdateDetail} class="flex flex-col space-y-4">
		<Label class="space-y-2">
			<span>제목</span>
			<Input type="text" name="title" value={post.title} />
		</Label>
		<Label class="space-y-2">
			<span>내용</span>
			<Textarea name="description" rows="4" value={post.description} />
		</Label>
		<Button type="submit">수정</Button>
	</form>
</Modal>
