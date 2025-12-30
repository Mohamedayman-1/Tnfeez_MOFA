Notifications WebSocket Guide

Overview
- Endpoint: ws://<HOST>:8000/ws/notifications/
- Secure: wss://<HOST>/ws/notifications/
- Auth: JWT access token via query param: ?token=<JWT_ACCESS>
- Per-user groups are handled server-side. The client only connects to the endpoint.

Server Behavior
- The backend uses Django Channels and routes WebSocket connections at /ws/notifications/.
- Authentication is done in the JWT middleware by decoding the access token.
- If no valid token is provided, the connection is rejected (anonymous users are not allowed).

Message Types
- connection_established
  - Sent on connect
  - Example payload:
    {"type":"connection_established","message":"WebSocket connected successfully","user_id":35}

- notification (general)
  - Example payload:
    {"type":"notification","message":"New budget transfer request created with code FAR-0016","data":{"transaction_id":860,"code":"FAR-0016"},"timestamp":"2025-12-30T12:40:49.474292"}

- oracle_upload_started
- oracle_upload_progress
- oracle_upload_completed
- oracle_upload_failed

Minimal React Integration
1) Create a WebSocket client that uses the access token.
2) Keep the socket open while the user is logged in.
3) Reconnect on close if needed.

Example (React hook)
```js
import { useEffect, useRef, useState } from "react";

export function useNotificationsSocket({ host, token }) {
  const wsRef = useRef(null);
  const [status, setStatus] = useState("disconnected");
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${host}/ws/notifications/?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((prev) => [...prev, data]);
      } catch (e) {
        // ignore non-JSON
      }
    };

    return () => {
      ws.close();
    };
  }, [host, token]);

  return { status, messages };
}
```

Usage Example
```js
const { status, messages } = useNotificationsSocket({
  host: "localhost:8000",
  token: accessToken,
});
```

Notes for Frontend
- Use the same access token used for REST API calls.
- Do not pass user_id in the query string when using a token.
- Keep the tab open. Closing or reloading will disconnect the socket.
- If the user logs out, close the socket and clear it.

Troubleshooting
- If you see "Anonymous user tried to connect":
  - Token is missing/invalid or expired.
  - The token belongs to a different user.

- If you see disconnects with code 1001:
  - The browser closed the socket (page reload or tab closed).

- If messages are not received:
  - Confirm the user who created the transaction matches the token user.
  - Verify the backend log shows "notification_message sent successfully".

