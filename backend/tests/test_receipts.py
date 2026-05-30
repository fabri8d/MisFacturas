"""Tests del sistema de comprobantes de pago (Drive-based)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch


def _make_bill(uid, bill_id="bill-receipt-1", due="2026-06-15", paid=False):
    return {
        "id": bill_id, "user_id": uid, "name": "EPEC", "category": "electricidad",
        "amount": 10000.0, "due_date": due, "month": due[:7],
        "is_paid": paid, "drive_file_id": None, "drive_folder_id": None,
        "drive_web_view_link": None, "created_at": "2026-06-01T00:00:00+00:00",
    }


def _mock_drive_service(fake_sb, uid):
    """Retorna un mock de drive_service con helpers ya mockeados."""
    mock = MagicMock()
    mock.get_user_profile.return_value = {
        "drive_access_token": "tok",
        "drive_folder_id": "root-folder-id",
    }
    mock.get_drive_service = AsyncMock(return_value=MagicMock())
    mock.get_month_folder.return_value = "comprobantes-folder-id"
    mock.upload_file_to_folder.return_value = {
        "id": "drive-file-123",
        "name": "test.pdf",
        "webViewLink": "https://drive.google.com/view/test",
        "webContentLink": "https://drive.google.com/download/test",
    }
    return mock


# ── Upload ────────────────────────────────────────────────────────────────────

async def test_upload_receipt_marks_bill_paid(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID, paid=False)
    fake_supabase.seed_bills([bill])

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_user_profile.return_value = {
            "drive_access_token": "tok", "drive_folder_id": "root-folder-id"
        }
        mock_ds.get_drive_service = AsyncMock(return_value=MagicMock())
        mock_ds.get_month_folder.return_value = "folder-id"
        mock_ds.upload_file_to_folder.return_value = {
            "id": "drv-1", "name": "t.pdf",
            "webViewLink": "https://drive/view", "webContentLink": "https://drive/dl",
        }

        r = await client.post(
            f"/api/bills/{bill['id']}/receipts",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert r.status_code == 201
    body = r.json()
    assert body["driveFileId"] == "drv-1"
    assert body["fileName"] == "test.jpg"

    # Factura debe estar marcada como pagada
    bills_in_db = fake_supabase._stores.get("bills", [])
    updated_bill = next((b for b in bills_in_db if b["id"] == bill["id"]), None)
    assert updated_bill and updated_bill.get("is_paid") is True


async def test_upload_receipt_no_drive_connected(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_user_profile.return_value = {"drive_access_token": None}

        r = await client.post(
            f"/api/bills/{bill['id']}/receipts",
            files={"file": ("t.jpg", b"bytes", "image/jpeg")},
        )

    assert r.status_code == 400
    assert "Drive" in r.json()["detail"]


async def test_upload_receipt_no_due_date(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = {**_make_bill(TEST_USER_ID), "due_date": None}
    fake_supabase.seed_bills([bill])

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_user_profile.return_value = {
            "drive_access_token": "tok", "drive_folder_id": "root"
        }

        r = await client.post(
            f"/api/bills/{bill['id']}/receipts",
            files={"file": ("t.pdf", b"bytes", "application/pdf")},
        )

    assert r.status_code == 400
    assert "fecha" in r.json()["detail"].lower()


async def test_upload_receipt_wrong_bill(client, fake_supabase):
    from tests.conftest import TEST_USER_ID_B
    bill = _make_bill(TEST_USER_ID_B)
    fake_supabase.seed_bills([bill])

    r = await client.post(
        f"/api/bills/{bill['id']}/receipts",
        files={"file": ("t.jpg", b"bytes", "image/jpeg")},
    )
    assert r.status_code == 404


async def test_upload_receipt_invalid_type(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_user_profile.return_value = {
            "drive_access_token": "tok", "drive_folder_id": "root"
        }

        r = await client.post(
            f"/api/bills/{bill['id']}/receipts",
            files={"file": ("t.txt", b"text content", "text/plain")},
        )

    assert r.status_code == 415


async def test_upload_receipt_too_large(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])

    big_bytes = b"x" * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_user_profile.return_value = {
            "drive_access_token": "tok", "drive_folder_id": "root"
        }

        r = await client.post(
            f"/api/bills/{bill['id']}/receipts",
            files={"file": ("big.jpg", big_bytes, "image/jpeg")},
        )

    assert r.status_code == 413


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_receipts_empty(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])

    r = await client.get(f"/api/bills/{bill['id']}/receipts")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_receipts(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])

    # Pre-seed receipts
    for i in range(2):
        fake_supabase._stores.setdefault("receipts", []).append({
            "id": f"rcpt-{i}", "user_id": TEST_USER_ID, "bill_id": bill["id"],
            "drive_file_id": f"drv-{i}", "drive_folder_id": "fldr",
            "file_name": f"receipt{i}.pdf", "file_size": 1024, "mime_type": "application/pdf",
            "drive_web_view_link": f"https://drive/view/{i}",
            "drive_web_content_link": f"https://drive/dl/{i}",
            "uploaded_at": "2026-06-01T10:00:00+00:00",
        })

    r = await client.get(f"/api/bills/{bill['id']}/receipts")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["driveWebViewLink"].startswith("https://")


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_receipt(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])
    fake_supabase._stores.setdefault("receipts", []).append({
        "id": "rcpt-del", "user_id": TEST_USER_ID, "bill_id": bill["id"],
        "drive_file_id": "drv-del", "drive_folder_id": "fldr",
        "file_name": "to_delete.pdf", "file_size": 512, "mime_type": "application/pdf",
        "drive_web_view_link": None, "drive_web_content_link": None,
        "uploaded_at": "2026-06-01T10:00:00+00:00",
    })

    mock_service = MagicMock()
    mock_service.files().delete().execute.return_value = None

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_drive_service = AsyncMock(return_value=mock_service)

        r = await client.delete(f"/api/bills/{bill['id']}/receipts/rcpt-del")

    assert r.status_code == 204
    # Receipt debe haber sido eliminado de Supabase
    receipts_left = fake_supabase._stores.get("receipts", [])
    assert not any(r["id"] == "rcpt-del" for r in receipts_left)


async def test_delete_receipt_drive_404_still_succeeds(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill = _make_bill(TEST_USER_ID)
    fake_supabase.seed_bills([bill])
    fake_supabase._stores.setdefault("receipts", []).append({
        "id": "rcpt-404", "user_id": TEST_USER_ID, "bill_id": bill["id"],
        "drive_file_id": "drv-gone", "drive_folder_id": "fldr",
        "file_name": "gone.pdf", "file_size": 512, "mime_type": "application/pdf",
        "drive_web_view_link": None, "drive_web_content_link": None,
        "uploaded_at": "2026-06-01T10:00:00+00:00",
    })

    mock_service = MagicMock()
    mock_service.files().delete().execute.side_effect = Exception("File not found")

    with patch("main.drive_service") as mock_ds:
        mock_ds.get_drive_service = AsyncMock(return_value=mock_service)

        r = await client.delete(f"/api/bills/{bill['id']}/receipts/rcpt-404")

    # Debe retornar 204 aunque Drive falle (archivo ya eliminado)
    assert r.status_code == 204


async def test_delete_receipt_wrong_user(client, fake_supabase):
    from tests.conftest import TEST_USER_ID_B
    bill = _make_bill(TEST_USER_ID_B)
    fake_supabase.seed_bills([bill])
    fake_supabase._stores.setdefault("receipts", []).append({
        "id": "rcpt-other", "user_id": TEST_USER_ID_B, "bill_id": bill["id"],
        "drive_file_id": "drv-x", "drive_folder_id": "fldr",
        "file_name": "other.pdf", "file_size": 512, "mime_type": "application/pdf",
        "drive_web_view_link": None, "drive_web_content_link": None,
        "uploaded_at": "2026-06-01T10:00:00+00:00",
    })

    r = await client.delete(f"/api/bills/{bill['id']}/receipts/rcpt-other")
    assert r.status_code == 404


# ── Summary ────────────────────────────────────────────────────────────────────

async def test_receipt_counts_summary(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    bill_a = _make_bill(TEST_USER_ID, "bill-A")
    bill_b = _make_bill(TEST_USER_ID, "bill-B")
    fake_supabase.seed_bills([bill_a, bill_b])

    receipts = fake_supabase._stores.setdefault("receipts", [])
    for i in range(2):
        receipts.append({
            "id": f"r-a-{i}", "user_id": TEST_USER_ID, "bill_id": "bill-A",
            "drive_file_id": f"drv-a-{i}", "drive_folder_id": "fldr",
            "file_name": f"a{i}.pdf", "file_size": 100, "mime_type": "application/pdf",
            "drive_web_view_link": None, "drive_web_content_link": None,
            "uploaded_at": "2026-06-01T10:00:00+00:00",
        })
    receipts.append({
        "id": "r-b-0", "user_id": TEST_USER_ID, "bill_id": "bill-B",
        "drive_file_id": "drv-b-0", "drive_folder_id": "fldr",
        "file_name": "b0.pdf", "file_size": 100, "mime_type": "application/pdf",
        "drive_web_view_link": None, "drive_web_content_link": None,
        "uploaded_at": "2026-06-01T10:00:00+00:00",
    })

    r = await client.get("/api/bills/receipts/summary")
    assert r.status_code == 200
    data = r.json()
    assert data.get("bill-A") == 2
    assert data.get("bill-B") == 1


# ── organize_bill_file ────────────────────────────────────────────────────────

async def test_organize_bill_file_calls_correct_folders():
    """organize_bill_file llama get_month_folder con los parámetros correctos."""
    from tests.conftest import TEST_USER_ID
    from unittest.mock import AsyncMock, patch

    bill = {
        "id": "test-bill", "user_id": TEST_USER_ID,
        "drive_file_id": "drv-abc", "drive_folder_id": "old-folder",
        "due_date": "2026-06-15",
    }

    mock_service = MagicMock()
    mock_service.files().update().execute.return_value = {
        "id": "drv-abc", "webViewLink": "https://drive/view/new"
    }

    with patch("drive_service.get_drive_service", AsyncMock(return_value=mock_service)), \
         patch("drive_service.get_user_profile", return_value={"drive_folder_id": "root-id"}), \
         patch("drive_service.get_month_folder", return_value="new-folder-id") as mock_gmf, \
         patch("drive_service.move_file", return_value={"webViewLink": "https://new"}) as mock_mv:
        import drive_service
        result = await drive_service.organize_bill_file(bill, TEST_USER_ID)

    assert result is not None
    mock_gmf.assert_called_once()
    # El primer argumento de get_month_folder debe ser el root_folder_id
    args = mock_gmf.call_args[0]
    assert args[0] == "root-id"
    assert args[2] == "Facturas"
    mock_mv.assert_called_once()
