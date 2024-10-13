<script>
	import { Heading, Button } from 'flowbite-svelte';
	import Section from '../Section.svelte';
</script>

<Section>
	<div slot="content" class="text-center">
		<Heading tag="h4">삭제가 완료되었습니다.</Heading>
	</div>
	<div slot="footer" class="text-center">
		<Button class="mt-5 px-8" href="/" size="sm" outline pill>돌아가기</Button>
	</div>
</Section>
