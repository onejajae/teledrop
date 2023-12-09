<script>
	export let src;
	import PdfViewer from 'svelte-pdf';
</script>

<PdfViewer url={src} showBorder={false} showButtons={['navigation']}></PdfViewer>
