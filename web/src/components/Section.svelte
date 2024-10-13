<script>
	import { Heading } from 'flowbite-svelte';
</script>

<section class="space-y-3 rounded-xl bg-gray-100 p-3 shadow-xl dark:bg-gray-700">
	<div class="flex items-center justify-between">
		<div>
			<Heading class="mx-1" tag="h4">
				<slot name="title" />
			</Heading>
		</div>
		<slot name="control" />
	</div>
	<slot name="content" />
	<slot name="footer" />
</section>
