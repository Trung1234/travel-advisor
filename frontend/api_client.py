import httpx


class ApiClientError(RuntimeError):
    pass


def send_chat_message(api_base_url: str, message: str, conversation_id: str | None = None) -> dict:
    payload = {"message": message, "conversation_id": conversation_id}
    response = httpx.post(f"{api_base_url}/api/v1/chat", json=payload, timeout=30)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        message = detail or str(exc)
        raise ApiClientError(message) from exc
    return response.json()


def request_tts_audio(api_base_url: str, text: str) -> bytes:
    response = httpx.post(f"{api_base_url}/api/v1/tts", json={"text": text}, timeout=30)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        message = detail or str(exc)
        raise ApiClientError(message) from exc
    return response.content
