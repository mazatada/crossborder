# Webhook Retry Policy

## Overview

The system implements a robust retry mechanism for Webhooks to ensure reliable delivery of events (e.g., `PN_SUBMITTED`, `DOCS_PACKAGED`) to external systems.

## Retry Logic

1.  **Initial Attempt**: The Webhook is attempted immediately within the job processing flow.
2.  **Failure Handling**: If the initial attempt fails (e.g., network error, 5xx response), a dedicated `webhook_retry` job is enqueued.
3.  **Backoff Strategy**: The retry job uses an exponential backoff or fixed interval strategy based on `attempts`.
4.  **Max Attempts**: Retries continue until `WEBHOOK_RETRY_MAX_ATTEMPTS` is reached. After that, the job is marked as `failed` (NonRetriable).

## Configuration

The following environment variables control the retry behavior:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `WEBHOOK_RETRY_MAX_ATTEMPTS` | `5` | Maximum number of retry attempts. |
| `WEBHOOK_RETRY_BASE_SEC` | `30` | Base seconds for backoff calculation (or fixed interval). |

## Observability

- **Audit Logs**:
    - `WEBHOOK_POST_FAILED`: Recorded when a webhook attempt fails.
    - `WEBHOOK_RETRY_ENQUEUE_FAILED`: Recorded if the retry job cannot be enqueued.
    - `JOB_FAILED` (retriable=False): Recorded when max attempts are exceeded.

- **Logs**: Application logs will show `WARNING` or `ERROR` level logs for webhook failures.
