# FastAPI/Starlette 기반 HTTP 파일 스트리밍 구조

## 1. 개요

대용량 파일이나 미디어(동영상, 오디오)를 클라이언트(예: 웹 브라우저)로 전송할 때, 전체 파일을 한 번에 보내는 것은 비효율적입니다. 대신 파일의 일부를 요청하고 응답받는 **HTTP Range 요청**과, 응답을 작은 조각(chunk)으로 나누어 순차적으로 보내는 **스트리밍** 방식이 사용됩니다.

이 문서는 FastAPI와 Starlette의 `StreamingResponse`를 중심으로 서버가 클라이언트의 Range 요청을 어떻게 처리하고, 파일 내용을 어떻게 스트리밍하는지, 그리고 클라이언트(브라우저)는 이를 어떻게 받아 처리하는지에 대한 구조를 설명합니다.

---

## 2. 주요 구성 요소 및 동작 흐름

### 2.1. 클라이언트 (웹 브라우저)

- **HTTP Range 요청**:
  - 클라이언트는 파일의 특정 부분만을 요청하기 위해 HTTP 헤더에 `Range: bytes=<start>-<end>` 또는 `Range: bytes=<start>-` 형태로 요청합니다.
  - 예: `Range: bytes=0-1048575` (첫 1MB 요청)
  - 동영상 스트리밍의 경우, 플레이어는 필요한 부분을 순차적으로 또는 탐색(seek) 위치에 따라 여러 번의 Range 요청을 보낼 수 있습니다.

- **응답 처리**:
  - 서버로부터 `206 Partial Content`(부분 응답) 또는 `200 OK`(전체 응답이지만 Range 요청에 대한 응답일 경우) 상태 코드와 함께 응답을 받습니다.
  - 응답 바디(HTTP Response Body)는 스트리밍 형태로 도착하며, 브라우저는 이를 받아 버퍼링하거나 즉시 재생합니다.
  - 개발자 도구의 네트워크 탭에서는 **하나의 Range 요청에 대해 하나의 요청-응답 쌍**으로 표시됩니다.

### 2.2. 서버 (FastAPI/Starlette)

- **라우터 (Router)**:
  - 클라이언트의 HTTP 요청을 받아 처리합니다.
  - `Range` 헤더를 파싱하여 `start` 및 `end` 오프셋을 결정합니다.
  - 파일 스트리밍을 담당하는 핸들러(Handler)를 호출합니다.

- **핸들러 (Handler)**:
  - 파싱된 `start`, `end` 값을 기반으로 실제 파일 시스템 또는 스토리지에서 해당 범위의 데이터를 읽어올 준비를 합니다.
  - 이때 `AsyncGenerator[bytes, None]` 형태의 비동기 제너레이터를 반환합니다. 이 제너레이터는 파일의 특정 부분을 정해진 크기(예: 1MB)의 청크(chunk) 단위로 `yield` 합니다.

  ```python
  # 예시: app/infrastructure/storage/local.py - read_file_range 메서드
  async def read_file_range(self, file_path: str, start: int, end: int) -> AsyncGenerator[bytes, None]:
      chunk_size = 1024 * 1024  # 1MB 청크
      async with await anyio.open_file(full_path, "rb") as f:
          await f.seek(start)
          pos = await f.tell()
          while pos <= end:
              remaining_size = end + 1 - pos
              read_size = min(chunk_size, remaining_size)
              data = await f.read(read_size)
              if not data: break
              pos += len(data)  # 실제 읽은 만큼 pos 증가 (중요)
              yield data
  ```

- **`StreamingResponse`**:
  - 핸들러로부터 반환된 비동기 제너레이터(`async_file_streamer`)를 FastAPI/Starlette의 `StreamingResponse` 객체에 전달합니다.
  - `StreamingResponse`는 이 제너레이터를 내부적으로 비동기적으로 순회(`async for chunk in async_file_streamer:`)하면서, 각 `yield`된 청크를 HTTP 응답 바디의 일부로 클라이언트에 전송합니다.
  - **하나의 HTTP 응답 내에서 여러 번의 `yield`가 발생**하며, 각 `yield`된 데이터 청크가 순차적으로 클라이언트에 스트리밍됩니다.

  ```python
  # 예시: app/routers/api/drop_router.py
  response = StreamingResponse(
      async_file_streamer,  # 비동기 제너레이터
      status_code=status.HTTP_206_PARTIAL_CONTENT,
      media_type=file_obj.file_type,
      headers=headers  # Content-Range, Content-Length 등 포함
  )
  return response
  ```

---

## 3. 핵심 상호작용 및 개념

- **요청-응답 매칭**:
  - 클라이언트가 보낸 **각각의 HTTP Range 요청은 서버에서 하나의 HTTP 응답**을 생성합니다.
  - 로그나 개발자 도구에서 관찰할 때, 요청 수와 응답 수는 동일하게 나타납니다.

- **서버 내부 청킹(Chunking) vs. 단일 HTTP 응답**:
  - 서버가 내부적으로 응답할 데이터를 여러 작은 청크로 나누어 `yield` 할지라도, 이 모든 청크들은 **하나의 HTTP 응답 스트림**을 구성합니다.
  - 클라이언트는 하나의 응답에 대해 순차적으로 도착하는 데이터 스트림을 받게 됩니다. `yield` 마다 새로운 HTTP 응답이 생성되는 것이 아닙니다.

- **스트리밍과 흐름 제어 (Flow Control)**:
  - **클라이언트의 수신 속도에 맞춰 서버가 전송 속도를 조절**합니다.
  - 만약 클라이언트(예: 브라우저의 비디오 플레이어)가 데이터 수신을 일시 중지하거나 네트워크 버퍼가 가득 차면, 클라이언트는 TCP 레벨에서 더 이상 데이터를 받지 않습니다.
  - 이 경우, 서버의 `StreamingResponse` 내부에서 제너레이터의 다음 `yield`는 블록(대기 상태)됩니다. 즉, 서버는 클라이언트가 다시 데이터를 읽을 준비가 될 때까지 데이터 전송을 멈춥니다.
  - 클라이언트가 재생을 재개하거나 버퍼에 여유가 생기면, 서버는 중단된 지점부터 다시 데이터 청크를 `yield`하여 전송을 이어갑니다.

---

## 4. 정리

- 클라이언트의 각 Range 요청은 서버의 단일 HTTP 응답에 해당합니다.
- 서버는 `StreamingResponse`와 비동기 제너레이터를 사용하여 응답 데이터를 여러 청크로 나누어 효율적으로 스트리밍합니다.
- 각 `yield`된 청크는 즉시 클라이언트로 전송 시도되지만, 실제 전송은 네트워크 스택과 클라이언트의 수신 상태에 따라 조절됩니다.
- 클라이언트가 데이터 수신을 일시 중지하면, 서버의 스트리밍 또한 일시 중지되어 불필요한 네트워크 트래픽과 서버 부하를 방지합니다.

이러한 구조는 대용량 데이터를 효율적으로 전송하고, 사용자 경험을 향상시키는 데 중요한 역할을 합니다.

---

## 5. 동기 처리와 비동기 처리의 차이점

### 5.1. 동기(synchronous) 처리의 한계

- 서버가 **동기 방식**으로 파일 IO 및 핸들러를 처리할 경우, 한 요청이 파일을 읽거나 클라이언트로 데이터를 전송하는 동안 **이벤트 루프(혹은 프로세스)가 점유**됩니다.
- 만약 클라이언트가 스트리밍 중 일시정지(데이터 수신 중단) 상태가 되면, 서버의 파일 읽기/전송 코드가 소켓 버퍼가 가득 찰 때까지 진행하다가, 더 이상 쓸 수 없으면 해당 코드에서 **블록(block)** 됩니다.
- 이 상태에서는 **서버가 다른 클라이언트의 요청을 처리할 수 없습니다.**
- 즉, 단일 프로세스/스레드 환경에서 동기 IO는 서버 전체를 "멈춘 것처럼" 만들 수 있습니다.

#### 예시
- 서버 프로세스 1개, 동기 파일 IO, 동기 핸들러
- 클라이언트 A가 스트리밍 요청 후 일시정지 → 서버가 블록됨
- 클라이언트 B가 새로운 요청을 보내도, A의 스트리밍이 끝나기 전까지 B의 요청은 대기 상태

### 5.2. 비동기(asynchronous) 처리의 장점

- **비동기 IO와 비동기 핸들러**를 사용하면, 한 요청이 네트워크/파일 IO에서 대기(await)하는 동안 **이벤트 루프가 다른 요청을 처리**할 수 있습니다.
- 즉, 한 클라이언트가 일시정지로 인해 대기 상태가 되어도, 서버는 다른 클라이언트의 요청을 동시에 처리할 수 있습니다.
- FastAPI/Starlette/Uvicorn 등 ASGI 기반 서버는 비동기 처리를 기본으로 지원하므로, **핸들러와 파일 IO 모두 async/await로 작성**하는 것이 필수적입니다.

#### 예시
- 서버 프로세스 1개, 비동기 파일 IO, 비동기 핸들러
- 클라이언트 A가 스트리밍 요청 후 일시정지 → await에서 대기
- 클라이언트 B의 요청이 즉시 처리됨 (서버가 멈추지 않음)

### 5.3. 실무 권장사항

- **동기 IO는 반드시 피하고, 비동기 IO를 사용**해야 합니다.
- 동기 IO를 쓸 수밖에 없다면, 여러 프로세스(worker)로 서버를 띄우거나, 별도의 스레드/프로세스에서 동기 IO를 처리해야 합니다.
- Python의 FastAPI/Starlette 환경에서는 파일 IO, DB IO, 네트워크 IO 등 모든 I/O 작업을 async/await로 작성하는 것이 서버의 동시성, 확장성, 안정성에 매우 중요합니다. 