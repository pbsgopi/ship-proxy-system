# ship-proxy-system
# Ship-to-Shore Single Connection Proxy

## 🚢 Overview

This project implements a cost-saving proxy system designed for environments with metered TCP connections, such as a cruise ship using satellite internet. The system funnels all HTTP and HTTPS requests from the ship's local network through a **single, persistent TCP connection** to an offshore server. This dramatically reduces costs when the provider's billing is based on the number of connections rather than the total data transferred.

The system consists of two main components:
1.  **Ship Proxy (Client)**: An HTTP proxy server that runs on the ship. It accepts requests from clients (like web browsers), queues them, and forwards them sequentially.
2.  **Offshore Proxy (Server)**: A remote server that receives the serialized requests, forwards them to the public internet, and sends responses back through the same single TCP connection.



---

## ✨ Features

- **Cost-Effective**: Uses only one outgoing TCP connection, minimizing per-connection charges.
- **Sequential Processing**: Handles requests one by one, ensuring reliability over potentially unstable links.
- **Full HTTP Support**: Works with all standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`, etc.).
- **HTTPS Tunneling**: Supports HTTPS traffic via the `HTTP CONNECT` method.
- **Dockerized**: Fully containerized with Docker and Docker Compose for easy setup and deployment.

---

## 🔧 Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Docker**: [Get Docker](https://www.docker.com/get-started)
- **Docker Compose**: (Included with Docker Desktop)

---

## 🚀 Getting Started

Follow these steps to get the proxy system up and running on your local machine.

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/ship-proxy-system.git](https://github.com/your-username/ship-proxy-system.git)
cd ship-proxy-system
```

### 2. Project Structure

The repository is organized into two main services:

```
ship-proxy-system/
├── ship-proxy/          # The client proxy running on the ship
│   ├── client.py
│   └── Dockerfile
├── offshore-proxy/      # The server proxy running offshore
│   ├── server.py
│   └── Dockerfile
└── docker-compose.yml   # Orchestrates the two services
```

### 3. Build and Run the System

Use Docker Compose to build the images and start the containers in detached mode.

```bash
docker compose build
```

Then, start the services:

```bash
docker compose up -d
```

You can verify that both containers are running with `docker ps`. The `ship-proxy` will be listening on port `8080` and the `offshore-proxy` on `9999`.

---

## 🛠️ Usage & Testing

The **Ship Proxy** is now running and listening on `http://localhost:8080`. You can test it using `curl` or by configuring it in your web browser's proxy settings.

#### Test HTTP Request

```bash
# On macOS/Linux
curl -x http://localhost:8080 [http://httpforever.com/](http://httpforever.com/)

# On Windows (PowerShell)
curl.exe -x http://localhost:8080 [http://httpforever.com/](http://httpforever.com/)
```
You should see the HTML content of the website.

#### Test HTTPS Request (via CONNECT tunnel)

```bash
# On macOS/Linux
curl -x http://localhost:8080 [https://www.google.com/](https://www.google.com/) -I

# On Windows (PowerShell)
curl.exe -x http://localhost:8080 [https://www.google.com/](https://www.google.com/) -I
```
You should see the HTTP headers for a `301 Moved Permanently` response from Google.

#### View Logs

To see the real-time logs from both containers and watch the requests being processed, use:
```bash
docker compose logs -f
```

---

## ⚙️ How It Works

### Custom TCP Protocol

To send multiple, distinct requests over a single TCP stream, we use a custom framing protocol. Each message (request or response) is wrapped in a frame with a simple header:

- **`[ 4-byte Length ]`**: The total length of the payload (Request ID + HTTP Data).
- **`[ 16-byte Request ID ]`**: A unique UUID to match responses with their original requests.
- **`[ HTTP Payload ]`**: The raw bytes of the HTTP request or response.

### Sequential Queuing

The **Ship Proxy** uses a queue to handle concurrent requests from multiple clients. A single worker thread processes this queue, ensuring that requests are sent to the **Offshore Proxy** strictly one after another. This prevents interleaving and simplifies the protocol.

---

## Shutting Down

To stop and remove the containers and network, run:
```bash
docker compose down
```
