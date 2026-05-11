import json
import os
from unittest.mock import MagicMock, patch

import pytest
from app.config import reset_settings_cache
from app.db import Base, get_engine, reset_engine_cache
from app.models import ExecutionEventRecord, ProofIngestOutbox
from app.verification_queue import (
    build_proof_ingested_envelope,
    envelope_to_json_bytes,
    publish_outbox_row,
    publish_pending_outbox,
    should_enqueue_to_outbox,
)


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch, tmp_path_factory):
    if "INTENTPROOF_DATABASE_URL" not in os.environ:
        p = tmp_path_factory.mktemp("verification_queue_db") / "default.db"
        monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{p}")
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_should_enqueue_false_without_queue_url(monkeypatch):
    monkeypatch.delenv("INTENTPROOF_SQS_QUEUE_URL", raising=False)
    reset_settings_cache()
    assert should_enqueue_to_outbox() is False


def test_should_enqueue_true_when_queue_url_set(monkeypatch):
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123456789012/q",
    )
    reset_settings_cache()
    assert should_enqueue_to_outbox() is True


def test_build_envelope_v1_shape():
    env = build_proof_ingested_envelope(
        tenant_id="t1",
        record_id=42,
        event_hash="deadbeef",
        correlation_id="corr-1",
        action="checkout.capture",
        message_id="00000000-0000-4000-8000-000000000001",
    )
    assert env["schema_version"] == 1
    assert env["type"] == "intentproof.proof.ingested"
    assert env["message_id"] == "00000000-0000-4000-8000-000000000001"
    assert env["tenant_id"] == "t1"
    assert env["execution_event_row_id"] == 42
    assert env["event_hash"] == "deadbeef"
    assert env["correlation_id"] == "corr-1"
    assert env["action"] == "checkout.capture"


def test_envelope_json_stable_sort_keys():
    env = build_proof_ingested_envelope(
        tenant_id="t",
        record_id=1,
        event_hash="h",
        correlation_id=None,
        action="a",
        message_id="m1",
    )
    s = envelope_to_json_bytes(env)
    parsed = json.loads(s)
    assert parsed["schema_version"] == 1
    assert list(json.loads(s).keys()) == sorted(json.loads(s).keys())


@patch("app.verification_queue.send_envelope_to_sqs")
def test_publish_outbox_row_success(mock_send, monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'p.db'}")
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123/q",
    )
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = SessionLocal()
    ev = ExecutionEventRecord(
        tenant_id="t",
        event_hash="h",
        correlation_id=None,
        action="a",
        raw_event={},
    )
    db.add(ev)
    db.flush()
    env_body = envelope_to_json_bytes(
        build_proof_ingested_envelope(
            tenant_id="t",
            record_id=ev.id,
            event_hash="h",
            correlation_id=None,
            action="a",
            message_id="mid",
        )
    )
    ob = ProofIngestOutbox(
        execution_event_id=ev.id,
        tenant_id="t",
        payload_json=env_body,
        publish_attempts=0,
    )
    db.add(ob)
    db.commit()
    oid = ob.id
    db.close()

    db2 = SessionLocal()
    assert publish_outbox_row(db2, oid) is True
    mock_send.assert_called_once_with(env_body)
    row = db2.get(ProofIngestOutbox, oid)
    assert row.published_at is not None
    assert row.last_error is None
    db2.close()
    reset_engine_cache()


@patch("app.verification_queue.send_envelope_to_sqs")
def test_publish_outbox_row_failure_increments_attempts(mock_send, monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'f.db'}")
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123/q",
    )
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = SessionLocal()
    ev = ExecutionEventRecord(
        tenant_id="t",
        event_hash="h2",
        correlation_id=None,
        action="a",
        raw_event={},
    )
    db.add(ev)
    db.flush()
    env_body = envelope_to_json_bytes(
        build_proof_ingested_envelope(
            tenant_id="t",
            record_id=ev.id,
            event_hash="h2",
            correlation_id=None,
            action="a",
            message_id="mid",
        )
    )
    ob = ProofIngestOutbox(
        execution_event_id=ev.id,
        tenant_id="t",
        payload_json=env_body,
        publish_attempts=0,
    )
    db.add(ob)
    db.commit()
    oid = ob.id
    db.close()

    mock_send.side_effect = RuntimeError("sqs down")
    db2 = SessionLocal()
    assert publish_outbox_row(db2, oid) is False
    row = db2.get(ProofIngestOutbox, oid)
    assert row.published_at is None
    assert row.publish_attempts == 1
    assert row.last_error is not None
    db2.close()
    reset_engine_cache()


@patch("boto3.client")
def test_send_uses_region_when_configured(mock_client, monkeypatch):
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.eu-west-1.amazonaws.com/123/q",
    )
    monkeypatch.setenv("INTENTPROOF_AWS_REGION", "eu-west-1")
    reset_settings_cache()
    mock_client.return_value.send_message = MagicMock()

    from app.verification_queue import send_envelope_to_sqs

    send_envelope_to_sqs('{"a":1}')
    mock_client.assert_called_once_with("sqs", region_name="eu-west-1")


@patch("app.verification_queue._sqs_client")
def test_send_envelope_noop_when_queue_url_unset(mock_sqs, monkeypatch):
    monkeypatch.delenv("INTENTPROOF_SQS_QUEUE_URL", raising=False)
    reset_settings_cache()
    from app.verification_queue import send_envelope_to_sqs

    send_envelope_to_sqs("{}")
    mock_sqs.assert_not_called()


def test_publish_outbox_short_circuits_when_queue_unset(monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'nq.db'}")
    monkeypatch.delenv("INTENTPROOF_SQS_QUEUE_URL", raising=False)
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)()
    try:
        assert publish_outbox_row(db, 999_999) is True
    finally:
        db.close()
    reset_engine_cache()


def test_publish_outbox_missing_row_returns_false(monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'm.db'}")
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123/q",
    )
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)()
    try:
        assert publish_outbox_row(db, 42_424_242) is False
    finally:
        db.close()
    reset_engine_cache()


@patch("app.verification_queue.send_envelope_to_sqs")
def test_publish_outbox_second_call_skips_when_already_published(mock_send, monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'id.db'}")
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123/q",
    )
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = SessionLocal()
    ev = ExecutionEventRecord(
        tenant_id="t",
        event_hash="hx",
        correlation_id=None,
        action="a",
        raw_event={},
    )
    db.add(ev)
    db.flush()
    body = envelope_to_json_bytes(
        build_proof_ingested_envelope(
            tenant_id="t",
            record_id=ev.id,
            event_hash="hx",
            correlation_id=None,
            action="a",
            message_id="mid",
        )
    )
    ob = ProofIngestOutbox(
        execution_event_id=ev.id,
        tenant_id="t",
        payload_json=body,
        publish_attempts=0,
    )
    db.add(ob)
    db.commit()
    oid = ob.id
    db.close()

    db2 = SessionLocal()
    assert publish_outbox_row(db2, oid) is True
    assert publish_outbox_row(db2, oid) is True
    assert mock_send.call_count == 1
    db2.close()
    reset_engine_cache()


def test_publish_pending_zero_when_queue_unset(monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'pz.db'}")
    monkeypatch.delenv("INTENTPROOF_SQS_QUEUE_URL", raising=False)
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = SessionLocal()
    ev = ExecutionEventRecord(
        tenant_id="t",
        event_hash="hz",
        correlation_id=None,
        action="a",
        raw_event={},
    )
    db.add(ev)
    db.flush()
    db.add(
        ProofIngestOutbox(
            execution_event_id=ev.id,
            tenant_id="t",
            payload_json="{}",
            publish_attempts=0,
        )
    )
    db.commit()
    db.close()

    db2 = SessionLocal()
    assert publish_pending_outbox(db2, limit=10) == 0
    db2.close()
    reset_engine_cache()


@patch("app.verification_queue.send_envelope_to_sqs")
def test_publish_pending_processes_batch(mock_send, monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'b.db'}")
    monkeypatch.setenv(
        "INTENTPROOF_SQS_QUEUE_URL",
        "https://sqs.us-east-1.amazonaws.com/123/q",
    )
    reset_settings_cache()
    reset_engine_cache()
    Base.metadata.create_all(bind=get_engine())

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = SessionLocal()
    for i in range(2):
        ev = ExecutionEventRecord(
            tenant_id="t",
            event_hash=f"h{i}",
            correlation_id=None,
            action="a",
            raw_event={},
        )
        db.add(ev)
        db.flush()
        body = envelope_to_json_bytes(
            build_proof_ingested_envelope(
                tenant_id="t",
                record_id=ev.id,
                event_hash=f"h{i}",
                correlation_id=None,
                action="a",
                message_id=f"m{i}",
            )
        )
        db.add(
            ProofIngestOutbox(
                execution_event_id=ev.id,
                tenant_id="t",
                payload_json=body,
                publish_attempts=0,
            )
        )
    db.commit()
    db.close()

    db2 = SessionLocal()
    n = publish_pending_outbox(db2, limit=10)
    assert n == 2
    assert mock_send.call_count == 2
    db2.close()
    reset_engine_cache()
