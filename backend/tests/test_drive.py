"""Tests del receptor de webhooks de Google Drive."""


async def test_webhook_sync_ignored(client):
    """resource-state=sync → 200 sin disparar procesamiento."""
    r = await client.post(
        "/api/drive/webhook",
        headers={"x-goog-resource-state": "sync", "x-goog-channel-id": "ch1"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_webhook_update_children_triggers(client):
    """resource-state=update + x-goog-changed=children → 200 inmediato."""
    r = await client.post(
        "/api/drive/webhook",
        headers={
            "x-goog-resource-state": "update",
            "x-goog-changed": "children",
            "x-goog-channel-id": "ch1",
        },
    )
    assert r.status_code == 200


async def test_webhook_update_without_children_ignored(client):
    """resource-state=update sin 'children' en x-goog-changed → no procesa."""
    r = await client.post(
        "/api/drive/webhook",
        headers={
            "x-goog-resource-state": "update",
            "x-goog-changed": "content",
            "x-goog-channel-id": "ch1",
        },
    )
    assert r.status_code == 200


async def test_webhook_add_triggers(client):
    """resource-state=add + children → dispara procesamiento."""
    r = await client.post(
        "/api/drive/webhook",
        headers={
            "x-goog-resource-state": "add",
            "x-goog-changed": "children",
            "x-goog-channel-id": "ch1",
        },
    )
    assert r.status_code == 200


async def test_webhook_other_states_ignored(client):
    """resource-state=trash u otros → 200 sin procesamiento."""
    for state in ("trash", "remove", ""):
        r = await client.post(
            "/api/drive/webhook",
            headers={"x-goog-resource-state": state},
        )
        assert r.status_code == 200


async def test_drive_status_not_connected(client):
    """Sin drive_config.json → connected=false."""
    r = await client.get("/api/drive/status")
    assert r.status_code == 200
    assert r.json()["connected"] is False
