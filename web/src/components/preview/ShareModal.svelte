<script>
	import { Heading, Img, Modal } from 'flowbite-svelte';

	export let open;
</script>

<Modal size="xs" bind:open autoclose outsideclose>
	<div class="flex flex-col">
		<Heading tag="h6">공유 QR코드</Heading>
		<Img src="https://placehold.co/200x200" />
	</div>
</Modal>
