<script>
	import { Heading, Button } from 'flowbite-svelte';
	import Section from '../../Section.svelte';
</script>

<Section>
	<div slot="content" class="grid text-center">
		<Heading tag="h4">권한이 없습니다.</Heading>
	</div>
	<div slot="footer" class="text-center">
		<Button class="my-3 px-8" href="/" size="sm" outline pill>돌아가기</Button>
	</div>
</Section>
