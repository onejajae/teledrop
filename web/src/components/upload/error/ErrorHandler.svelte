<script>
	import { is409Conflict } from '$utils/checkHTTPErrorType';
	import Conflict409 from './Conflict409.svelte';

	export let error;
</script>

{#if is409Conflict(error)}
	<Conflict409></Conflict409>
{:else if error.response.status === 413}
	파일이 너무 큽니다.
{:else}
	업로드 실패. 관리자에게 문의하십시오.
{/if}
