#!/usr/bin/env python3
"""Build and oracle-check five locally runnable ActiveGraph-50 systems."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from research.activegraph_task_runtime import canonical_json, evaluate

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SOURCE = ROOT / "research" / "activegraph_task_runtime.py"
API_REFERENCE = ROOT / "benchmarks" / "activegraph_50" / "ACTIVEGRAPH_API.md"
ACTIVEGRAPH_REVISION = "148e12c2969f18fa12a1a3c2e75f3affd9aa0616"
PUBLIC_CHECKS = 20
SEALED_CHECKS = 30
TOTAL_CHECKS = PUBLIC_CHECKS + SEALED_CHECKS
HIDDEN_CATEGORIES = (
    "typed_state",
    "relations",
    "policy",
    "composition",
    "adversarial",
    "restart_replay",
)
INTEGER_FIELDS = {
    "amount",
    "required",
    "approval_count",
    "quota",
    "used",
    "units",
    "priority",
    "sequence",
    "expires_at",
}
BOOLEAN_FIELDS = {"active"}
STRING_ARRAY_FIELDS = {"roles"}
OBJECT_VALUE_FIELDS = {"output"}


def _field_type(field_name: str) -> str:
    if field_name in INTEGER_FIELDS:
        return "integer"
    if field_name in BOOLEAN_FIELDS:
        return "boolean"
    if field_name in STRING_ARRAY_FIELDS:
        return "string_array"
    if field_name in OBJECT_VALUE_FIELDS:
        return "object"
    return "string"


@dataclass
class LogicalObject:
    type: str
    key: str
    data: dict[str, Any]
    version: int = 1


@dataclass
class ReferenceState:
    object_keys: dict[str, str]
    objects: dict[tuple[str, str], LogicalObject] = field(default_factory=dict)
    relations: set[tuple[str, str, str, str, str]] = field(default_factory=set)

    def get(self, object_type: str, key: str) -> LogicalObject | None:
        return self.objects.get((object_type, str(key)))

    def add(self, object_type: str, data: dict[str, Any]) -> LogicalObject:
        key_field = self.object_keys[object_type]
        key = str(data[key_field])
        if (object_type, key) in self.objects:
            raise ValueError(f"duplicate logical object: {object_type}/{key}")
        item = LogicalObject(object_type, key, json.loads(json.dumps(data)))
        self.objects[(object_type, key)] = item
        return item

    def patch(self, object_type: str, key: str, updates: dict[str, Any]) -> LogicalObject:
        item = self.objects[(object_type, str(key))]
        changed = any(item.data.get(name) != value for name, value in updates.items())
        if changed:
            item.data.update(json.loads(json.dumps(updates)))
            item.version += 1
        return item

    def relate(
        self,
        relation_type: str,
        source_type: str,
        source_key: str,
        target_type: str,
        target_key: str,
    ) -> None:
        self.relations.add((relation_type, source_type, str(source_key), target_type, str(target_key)))

    def snapshot(self) -> dict[str, Any]:
        objects = [
            {
                "type": item.type,
                "key": item.key,
                "data": json.loads(json.dumps(item.data)),
                "version": item.version,
            }
            for item in self.objects.values()
        ]
        objects.sort(key=lambda row: (row["type"], canonical_json(row["key"])))
        relations = [
            {
                "type": relation_type,
                "source": [source_type, source_key],
                "target": [target_type, target_key],
                "data": {},
            }
            for relation_type, source_type, source_key, target_type, target_key in self.relations
        ]
        relations.sort(key=canonical_json)
        return {"objects": objects, "relations": relations}


Handler = Callable[[ReferenceState, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    split: str
    title: str
    objective: str
    object_keys: dict[str, str]
    object_fields: dict[str, tuple[str, ...]]
    relation_types: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]
    operations: tuple[str, ...]
    specification: str
    invariants: tuple[str, ...]
    handler: Handler
    payloads: Callable[[], dict[str, list[dict[str, Any]]]]

    @property
    def pack_name(self) -> str:
        return "ouro_" + self.id

    def contract(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "task_id": self.id,
            "title": self.title,
            "split": self.split,
            "pack_name": self.pack_name,
            "activegraph_revision": ACTIVEGRAPH_REVISION,
            "request_event": "ouro.benchmark.requested",
            "result_event": "ouro.benchmark.completed",
            "object_keys": self.object_keys,
            "object_fields": {key: list(value) for key, value in self.object_fields.items()},
            "object_field_types": {
                object_type: {field_name: _field_type(field_name) for field_name in fields}
                for object_type, fields in self.object_fields.items()
            },
            "relation_types": {
                key: {"source_types": list(value[0]), "target_types": list(value[1])}
                for key, value in self.relation_types.items()
            },
            "operations": list(self.operations),
            "specification": self.specification,
            "invariants": list(self.invariants),
            "restart_after": {"transfer": 5},
            "score": {
                "public": PUBLIC_CHECKS,
                "sealed": SEALED_CHECKS,
                "total": TOTAL_CHECKS,
                "hard_gate": "exact Pack/object/relation surface and deterministic behavior only",
            },
        }


def _fingerprint(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "operation_id"}
    return hashlib.sha256(canonical_json(body).encode()).hexdigest()


def _process(definition: TaskDefinition, state: ReferenceState, payload: dict[str, Any]) -> dict[str, Any]:
    operation_id = str(payload["operation_id"])
    fingerprint = _fingerprint(payload)
    receipt = state.get("operation_receipt", operation_id)
    if receipt is not None:
        if receipt.data["fingerprint"] == fingerprint:
            return json.loads(json.dumps(receipt.data["output"]))
        return {"error": "operation_id_conflict", "operation_id": operation_id}
    output = definition.handler(state, payload)
    state.add(
        "operation_receipt",
        {"operation_id": operation_id, "fingerprint": fingerprint, "output": output},
    )
    return output


def _error(code: str, **details: Any) -> dict[str, Any]:
    return {"error": code, **details}


def _incident(state: ReferenceState, payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    if operation == "register_service":
        service_id = str(payload.get("service_id", ""))
        if not service_id or state.get("service", service_id):
            return _error("invalid_or_existing_service", service_id=service_id)
        state.add("service", {"service_id": service_id, "owner": str(payload.get("owner", "")), "status": "active"})
        return {"service_id": service_id, "registered": True}
    if operation == "open_incident":
        incident_id = str(payload.get("incident_id", ""))
        services = sorted({str(item) for item in payload.get("services", [])})
        severity = str(payload.get("severity", ""))
        missing = [item for item in services if not state.get("service", item)]
        if not incident_id or state.get("incident", incident_id):
            return _error("invalid_or_existing_incident", incident_id=incident_id)
        if severity not in {"low", "medium", "high", "critical"} or not services or missing:
            return _error("invalid_incident", missing_services=missing)
        state.add(
            "incident",
            {"incident_id": incident_id, "severity": severity, "status": "open", "responder": ""},
        )
        for service_id in services:
            state.relate("affects", "incident", incident_id, "service", service_id)
        return {"incident_id": incident_id, "status": "open", "affected": services}
    incident_id = str(payload.get("incident_id", ""))
    incident = state.get("incident", incident_id)
    if incident is None:
        return _error("incident_not_found", incident_id=incident_id)
    if operation == "acknowledge":
        if incident.data["status"] == "resolved":
            return _error("incident_already_resolved", incident_id=incident_id)
        responder = str(payload.get("responder", ""))
        if not responder:
            return _error("responder_required", incident_id=incident_id)
        state.patch("incident", incident_id, {"status": "acknowledged", "responder": responder})
    elif operation == "escalate":
        severity = str(payload.get("severity", ""))
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if severity not in order or order[severity] <= order[incident.data["severity"]]:
            return _error("severity_must_increase", incident_id=incident_id)
        state.patch("incident", incident_id, {"severity": severity})
    elif operation == "link_service":
        service_id = str(payload.get("service_id", ""))
        if not state.get("service", service_id):
            return _error("service_not_found", service_id=service_id)
        state.relate("affects", "incident", incident_id, "service", service_id)
    elif operation == "resolve":
        if incident.data["status"] != "acknowledged":
            return _error("acknowledgement_required", incident_id=incident_id)
        state.patch("incident", incident_id, {"status": "resolved"})
    else:
        return _error("unknown_operation", operation=operation)
    current = state.get("incident", incident_id)
    assert current is not None
    return {
        "incident_id": incident_id,
        "status": current.data["status"],
        "severity": current.data["severity"],
    }


def _approval(state: ReferenceState, payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    if operation == "register_user":
        user_id = str(payload.get("user_id", ""))
        roles = sorted({str(item) for item in payload.get("roles", [])})
        if not user_id or not roles or state.get("user", user_id):
            return _error("invalid_or_existing_user", user_id=user_id)
        state.add("user", {"user_id": user_id, "roles": roles})
        return {"user_id": user_id, "roles": roles}
    if operation == "create_request":
        request_id = str(payload.get("request_id_value", ""))
        requester = str(payload.get("requester", ""))
        amount = int(payload.get("amount", -1))
        if state.get("request", request_id) or not state.get("user", requester) or amount < 0:
            return _error("invalid_request", request_id=request_id)
        required = 1 if amount < 1_000 else 2
        state.add(
            "request",
            {
                "request_id": request_id,
                "requester": requester,
                "amount": amount,
                "required": required,
                "status": "pending",
                "approval_count": 0,
            },
        )
        state.relate("requested_by", "request", request_id, "user", requester)
        return {"request_id": request_id, "status": "pending", "required": required}
    request_id = str(payload.get("request_id_value", ""))
    request = state.get("request", request_id)
    if request is None:
        return _error("request_not_found", request_id=request_id)
    if operation == "approve":
        user_id = str(payload.get("user_id", ""))
        user = state.get("user", user_id)
        if request.data["status"] != "pending":
            return _error("request_not_pending", request_id=request_id)
        if user is None or user_id == request.data["requester"]:
            return _error("separation_of_duty", request_id=request_id)
        roles = set(user.data["roles"])
        if not roles & {"manager", "finance", "executive"}:
            return _error("approver_role_required", user_id=user_id)
        existing = [
            item
            for item in state.objects.values()
            if item.type == "approval" and item.data["request_id"] == request_id and item.data["user_id"] == user_id
        ]
        if existing:
            return _error("duplicate_approval", user_id=user_id)
        approval_id = f"{request_id}:{user_id}"
        state.add("approval", {"approval_id": approval_id, "request_id": request_id, "user_id": user_id})
        state.relate("approval_for", "approval", approval_id, "request", request_id)
        state.relate("approval_by", "approval", approval_id, "user", user_id)
        count = request.data["approval_count"] + 1
        status = "approved" if count >= request.data["required"] else "pending"
        state.patch("request", request_id, {"approval_count": count, "status": status})
    elif operation == "reject":
        user_id = str(payload.get("user_id", ""))
        user = state.get("user", user_id)
        if request.data["status"] != "pending" or user is None or "manager" not in user.data["roles"]:
            return _error("manager_rejection_required", request_id=request_id)
        state.patch("request", request_id, {"status": "rejected"})
    elif operation == "cancel":
        actor = str(payload.get("actor", ""))
        if actor != request.data["requester"] or request.data["status"] != "pending":
            return _error("requester_pending_cancel_only", request_id=request_id)
        state.patch("request", request_id, {"status": "cancelled"})
    else:
        return _error("unknown_operation", operation=operation)
    current = state.get("request", request_id)
    assert current is not None
    return {
        "request_id": request_id,
        "status": current.data["status"],
        "approval_count": current.data["approval_count"],
    }


def _promote_jobs(state: ReferenceState, tenant_id: str, used: int, quota: int) -> tuple[int, list[str]]:
    queued = [
        item
        for item in state.objects.values()
        if item.type == "job" and item.data["tenant_id"] == tenant_id and item.data["status"] == "queued"
    ]
    queued.sort(key=lambda item: (-item.data["priority"], item.data["sequence"], item.key))
    promoted: list[str] = []
    for item in queued:
        if used + item.data["units"] <= quota:
            used += item.data["units"]
            state.patch("job", item.key, {"status": "running"})
            promoted.append(item.key)
    return used, promoted


def _scheduler(state: ReferenceState, payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    tenant_id = str(payload.get("tenant_id", ""))
    if operation == "configure_tenant":
        quota = int(payload.get("quota", -1))
        if not tenant_id or quota < 0 or state.get("tenant", tenant_id):
            return _error("invalid_or_existing_tenant", tenant_id=tenant_id)
        state.add("tenant", {"tenant_id": tenant_id, "quota": quota, "used": 0})
        return {"tenant_id": tenant_id, "quota": quota, "used": 0}
    tenant = state.get("tenant", tenant_id)
    if tenant is None:
        return _error("tenant_not_found", tenant_id=tenant_id)
    if operation == "submit_job":
        job_id = str(payload.get("job_id", ""))
        units = int(payload.get("units", 0))
        priority = int(payload.get("priority", 0))
        if not job_id or units <= 0 or state.get("job", job_id):
            return _error("invalid_or_existing_job", job_id=job_id)
        running = tenant.data["used"] + units <= tenant.data["quota"]
        status = "running" if running else "queued"
        sequence = sum(1 for item in state.objects.values() if item.type == "job") + 1
        state.add(
            "job",
            {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "units": units,
                "priority": priority,
                "sequence": sequence,
                "status": status,
            },
        )
        state.relate("owned_by", "job", job_id, "tenant", tenant_id)
        if running:
            state.patch("tenant", tenant_id, {"used": tenant.data["used"] + units})
        return {"job_id": job_id, "status": status, "used": state.get("tenant", tenant_id).data["used"]}
    if operation == "resize_quota":
        quota = int(payload.get("quota", -1))
        if quota < tenant.data["used"]:
            return _error("quota_below_active_usage", tenant_id=tenant_id)
        used, promoted = _promote_jobs(state, tenant_id, tenant.data["used"], quota)
        state.patch("tenant", tenant_id, {"quota": quota, "used": used})
        return {"tenant_id": tenant_id, "quota": quota, "used": used, "promoted": promoted}
    job_id = str(payload.get("job_id", ""))
    job = state.get("job", job_id)
    if job is None or job.data["tenant_id"] != tenant_id:
        return _error("job_not_found", job_id=job_id)
    if operation not in {"complete_job", "cancel_job"} or job.data["status"] not in {"running", "queued"}:
        return _error("job_not_actionable", job_id=job_id)
    was_running = job.data["status"] == "running"
    final_status = "completed" if operation == "complete_job" else "cancelled"
    state.patch("job", job_id, {"status": final_status})
    used = tenant.data["used"] - (job.data["units"] if was_running else 0)
    used, promoted = _promote_jobs(state, tenant_id, used, tenant.data["quota"])
    state.patch("tenant", tenant_id, {"used": used})
    return {"job_id": job_id, "status": final_status, "used": used, "promoted": promoted}


def _provenance(state: ReferenceState, payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    if operation == "ingest":
        document_id = str(payload.get("document_id", ""))
        revision_id = str(payload.get("revision_id", ""))
        if (
            not document_id
            or not revision_id
            or state.get("document", document_id)
            or state.get("revision", revision_id)
        ):
            return _error("invalid_or_existing_document", document_id=document_id)
        state.add("document", {"document_id": document_id, "current_revision": revision_id, "status": "draft"})
        state.add(
            "revision",
            {
                "revision_id": revision_id,
                "document_id": document_id,
                "content_hash": str(payload.get("content_hash", "")),
                "status": "draft",
            },
        )
        state.relate("has_revision", "document", document_id, "revision", revision_id)
        return {"document_id": document_id, "revision_id": revision_id, "status": "draft"}
    if operation == "revise":
        document_id = str(payload.get("document_id", ""))
        document = state.get("document", document_id)
        revision_id = str(payload.get("revision_id", ""))
        if document is None or not revision_id or state.get("revision", revision_id):
            return _error("invalid_revision", revision_id=revision_id)
        previous = document.data["current_revision"]
        state.add(
            "revision",
            {
                "revision_id": revision_id,
                "document_id": document_id,
                "content_hash": str(payload.get("content_hash", "")),
                "status": "draft",
            },
        )
        state.relate("has_revision", "document", document_id, "revision", revision_id)
        state.relate("derived_from", "revision", revision_id, "revision", previous)
        state.patch("document", document_id, {"current_revision": revision_id, "status": "draft"})
        return {"document_id": document_id, "revision_id": revision_id, "previous": previous}
    revision_id = str(payload.get("revision_id", ""))
    revision = state.get("revision", revision_id)
    if revision is None:
        return _error("revision_not_found", revision_id=revision_id)
    document = state.get("document", revision.data["document_id"])
    assert document is not None
    if operation == "approve":
        if revision.data["status"] == "invalid":
            return _error("invalid_revision_cannot_approve", revision_id=revision_id)
        state.patch("revision", revision_id, {"status": "approved"})
        if document.data["current_revision"] == revision_id:
            state.patch("document", document.key, {"status": "approved"})
        return {"revision_id": revision_id, "status": "approved"}
    if operation == "invalidate":
        state.patch("revision", revision_id, {"status": "invalid"})
        invalidated = [revision_id]
        changed = True
        while changed:
            changed = False
            for relation in list(state.relations):
                kind, source_type, source_key, target_type, target_key = relation
                if kind != "derived_from" or target_key not in invalidated or source_key in invalidated:
                    continue
                state.patch("revision", source_key, {"status": "invalid"})
                invalidated.append(source_key)
                changed = True
        for item in list(state.objects.values()):
            if item.type == "document" and item.data["current_revision"] in invalidated:
                state.patch("document", item.key, {"status": "invalid"})
        return {"revision_id": revision_id, "invalidated": sorted(invalidated)}
    return _error("unknown_operation", operation=operation)


def _member_principals(state: ReferenceState, user_id: str) -> set[tuple[str, str]]:
    principals = {("user", user_id)}
    changed = True
    while changed:
        changed = False
        for kind, source_type, source_key, target_type, target_key in state.relations:
            if (
                kind == "member_of"
                and (source_type, source_key) in principals
                and (target_type, target_key) not in principals
            ):
                principals.add((target_type, target_key))
                changed = True
    return principals


def _would_cycle(state: ReferenceState, source_type: str, source_key: str, group_id: str) -> bool:
    if source_type != "group":
        return False
    return ("group", source_key) in _member_principals(state, group_id)


def _access(state: ReferenceState, payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    if operation in {"add_user", "add_group", "add_resource"}:
        object_type = operation.removeprefix("add_")
        key_field = state.object_keys[object_type]
        key = str(payload.get(key_field, ""))
        if not key or state.get(object_type, key):
            return _error("invalid_or_existing_entity", id=key)
        data = {key_field: key, "name": str(payload.get("name", key))}
        state.add(object_type, data)
        return {"type": object_type, "id": key, "created": True}
    if operation == "add_member":
        source_type = str(payload.get("principal_type", ""))
        source_key = str(payload.get("principal_id", ""))
        group_id = str(payload.get("group_id", ""))
        if (
            source_type not in {"user", "group"}
            or not state.get(source_type, source_key)
            or not state.get("group", group_id)
        ):
            return _error("invalid_membership")
        if source_type == "group" and (
            source_key == group_id or _would_cycle(state, source_type, source_key, group_id)
        ):
            return _error("membership_cycle")
        state.relate("member_of", source_type, source_key, "group", group_id)
        return {"principal": [source_type, source_key], "group_id": group_id, "member": True}
    if operation == "grant":
        grant_id = str(payload.get("grant_id", ""))
        principal_type = str(payload.get("principal_type", ""))
        principal_id = str(payload.get("principal_id", ""))
        resource_id = str(payload.get("resource_id", ""))
        effect = str(payload.get("effect", ""))
        if (
            not grant_id
            or state.get("grant", grant_id)
            or principal_type not in {"user", "group"}
            or not state.get(principal_type, principal_id)
            or not state.get("resource", resource_id)
            or effect not in {"allow", "deny"}
        ):
            return _error("invalid_grant", grant_id=grant_id)
        state.add(
            "grant",
            {
                "grant_id": grant_id,
                "principal_type": principal_type,
                "principal_id": principal_id,
                "resource_id": resource_id,
                "permission": str(payload.get("permission", "")),
                "effect": effect,
                "expires_at": int(payload.get("expires_at", 0)),
                "active": True,
            },
        )
        state.relate("grant_principal", principal_type, principal_id, "grant", grant_id)
        state.relate("grant_resource", "grant", grant_id, "resource", resource_id)
        return {"grant_id": grant_id, "active": True}
    if operation == "revoke":
        grant_id = str(payload.get("grant_id", ""))
        grant = state.get("grant", grant_id)
        if grant is None or not grant.data["active"]:
            return _error("grant_not_active", grant_id=grant_id)
        state.patch("grant", grant_id, {"active": False})
        return {"grant_id": grant_id, "active": False}
    if operation == "check_access":
        user_id = str(payload.get("user_id", ""))
        resource_id = str(payload.get("resource_id", ""))
        permission = str(payload.get("permission", ""))
        at = int(payload.get("at", 0))
        if not state.get("user", user_id) or not state.get("resource", resource_id):
            return _error("unknown_subject_or_resource")
        principals = _member_principals(state, user_id)
        grants = [
            item.data
            for item in state.objects.values()
            if item.type == "grant"
            and item.data["active"]
            and item.data["resource_id"] == resource_id
            and item.data["permission"] == permission
            and (item.data["expires_at"] == 0 or item.data["expires_at"] > at)
            and (item.data["principal_type"], item.data["principal_id"]) in principals
        ]
        denied = any(item["effect"] == "deny" for item in grants)
        allowed = bool(grants) and not denied
        reason = "explicit_deny" if denied else "active_grant" if allowed else "no_active_grant"
        return {
            "user_id": user_id,
            "resource_id": resource_id,
            "permission": permission,
            "allowed": allowed,
            "reason": reason,
        }
    return _error("unknown_operation", operation=operation)


def _ids(prefix: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        value = dict(row)
        value.setdefault("operation_id", f"{prefix}-{index:02d}")
        result.append(value)
    return result


def _incident_payloads() -> dict[str, list[dict[str, Any]]]:
    public = [{"operation": "register_service", "service_id": f"svc{i}", "owner": f"team{i % 4}"} for i in range(1, 9)]
    public += [
        {
            "operation": "open_incident",
            "incident_id": f"inc{i}",
            "severity": ("low", "medium", "high", "critical")[i % 4],
            "services": [f"svc{i}"],
        }
        for i in range(1, 7)
    ]
    public += [{"operation": "acknowledge", "incident_id": f"inc{i}", "responder": f"oncall{i}"} for i in range(1, 4)]
    public += [
        {"operation": "escalate", "incident_id": "inc1", "severity": "critical"},
        {"operation": "link_service", "incident_id": "inc2", "service_id": "svc8"},
        {"operation": "resolve", "incident_id": "inc1"},
    ]
    private = [
        {"operation": "register_service", "service_id": "api", "owner": "platform"},
        {"operation": "register_service", "service_id": "db", "owner": "storage"},
        {"operation": "register_service", "service_id": "queue", "owner": "platform"},
        {"operation": "open_incident", "incident_id": "p1", "severity": "medium", "services": ["api", "db"]},
        {"operation": "acknowledge", "incident_id": "p1", "responder": "ada"},
        {"operation": "link_service", "incident_id": "p1", "service_id": "queue"},
        {"operation": "escalate", "incident_id": "p1", "severity": "critical"},
        {"operation": "resolve", "incident_id": "p1"},
        {"operation": "resolve", "incident_id": "p1"},
        {"operation": "open_incident", "incident_id": "p2", "severity": "high", "services": ["db"]},
        {"operation": "resolve", "incident_id": "p2"},
        {"operation": "acknowledge", "incident_id": "p2", "responder": "lin"},
        {"operation": "escalate", "incident_id": "p2", "severity": "medium"},
        {"operation": "link_service", "incident_id": "missing", "service_id": "api"},
        {"operation": "open_incident", "incident_id": "bad", "severity": "urgent", "services": ["ghost"]},
        {"operation": "resolve", "incident_id": "p2"},
        {"operation": "register_service", "service_id": "api", "owner": "other"},
        {"operation": "acknowledge", "incident_id": "p2", "responder": ""},
        {"operation": "open_incident", "incident_id": "p3", "severity": "low", "services": ["api", "queue"]},
        {"operation": "escalate", "incident_id": "p3", "severity": "high"},
    ]
    transfer = [
        {"operation": "register_service", "service_id": "edge", "owner": "net"},
        {"operation": "register_service", "service_id": "auth", "owner": "security"},
        {"operation": "open_incident", "incident_id": "t1", "severity": "high", "services": ["edge", "auth"]},
        {"operation": "acknowledge", "incident_id": "t1", "responder": "sam"},
        {"operation": "escalate", "incident_id": "t1", "severity": "critical"},
        {"operation": "resolve", "incident_id": "t1"},
        {"operation": "open_incident", "incident_id": "t2", "severity": "low", "services": ["edge"]},
        {"operation": "acknowledge", "incident_id": "t2", "responder": "jo"},
        {"operation": "link_service", "incident_id": "t2", "service_id": "auth"},
        {"operation": "resolve", "incident_id": "t2"},
    ]
    return {
        "public": _ids("inc-pub", public),
        "private": _ids("inc-prv", private),
        "transfer": _ids("inc-xfer", transfer),
    }


def _approval_payloads() -> dict[str, list[dict[str, Any]]]:
    public = [
        {"operation": "register_user", "user_id": "req", "roles": ["employee"]},
        {"operation": "register_user", "user_id": "mgr", "roles": ["manager"]},
        {"operation": "register_user", "user_id": "fin", "roles": ["finance"]},
    ]
    public += [
        {"operation": "create_request", "request_id_value": f"r{i}", "requester": "req", "amount": amount}
        for i, amount in enumerate((10, 250, 999, 1000, 5000, 12000), start=1)
    ]
    public += [
        {"operation": "approve", "request_id_value": "r1", "user_id": "mgr"},
        {"operation": "approve", "request_id_value": "r4", "user_id": "mgr"},
        {"operation": "approve", "request_id_value": "r4", "user_id": "fin"},
        {"operation": "approve", "request_id_value": "r2", "user_id": "req"},
        {"operation": "cancel", "request_id_value": "r2", "actor": "req"},
        {"operation": "reject", "request_id_value": "r3", "user_id": "mgr"},
        {"operation": "approve", "request_id_value": "r5", "user_id": "fin"},
        {"operation": "approve", "request_id_value": "r5", "user_id": "mgr"},
        {"operation": "approve", "request_id_value": "missing", "user_id": "mgr"},
        {"operation": "register_user", "user_id": "aud", "roles": ["auditor"]},
        {"operation": "approve", "request_id_value": "r6", "user_id": "aud"},
    ]
    private = [
        {"operation": "register_user", "user_id": "alice", "roles": ["employee"]},
        {"operation": "register_user", "user_id": "bob", "roles": ["manager"]},
        {"operation": "register_user", "user_id": "cara", "roles": ["finance"]},
        {"operation": "register_user", "user_id": "dan", "roles": ["executive"]},
        {"operation": "create_request", "request_id_value": "small", "requester": "alice", "amount": 700},
        {"operation": "create_request", "request_id_value": "large", "requester": "alice", "amount": 7000},
        {"operation": "approve", "request_id_value": "small", "user_id": "bob"},
        {"operation": "approve", "request_id_value": "large", "user_id": "bob"},
        {"operation": "approve", "request_id_value": "large", "user_id": "cara"},
        {"operation": "approve", "request_id_value": "large", "user_id": "dan"},
        {"operation": "create_request", "request_id_value": "self", "requester": "bob", "amount": 5},
        {"operation": "approve", "request_id_value": "self", "user_id": "bob"},
        {"operation": "approve", "request_id_value": "self", "user_id": "cara"},
        {"operation": "approve", "request_id_value": "self", "user_id": "cara"},
        {"operation": "cancel", "request_id_value": "small", "actor": "alice"},
        {"operation": "create_request", "request_id_value": "reject", "requester": "alice", "amount": 40},
        {"operation": "reject", "request_id_value": "reject", "user_id": "cara"},
        {"operation": "reject", "request_id_value": "reject", "user_id": "bob"},
        {"operation": "create_request", "request_id_value": "bad", "requester": "ghost", "amount": -1},
        {"operation": "cancel", "request_id_value": "self", "actor": "ghost"},
    ]
    transfer = [
        {"operation": "register_user", "user_id": "u", "roles": ["employee"]},
        {"operation": "register_user", "user_id": "m", "roles": ["manager"]},
        {"operation": "register_user", "user_id": "f", "roles": ["finance"]},
        {"operation": "create_request", "request_id_value": "x", "requester": "u", "amount": 1500},
        {"operation": "approve", "request_id_value": "x", "user_id": "m"},
        {"operation": "approve", "request_id_value": "x", "user_id": "f"},
        {"operation": "create_request", "request_id_value": "y", "requester": "u", "amount": 1},
        {"operation": "cancel", "request_id_value": "y", "actor": "u"},
        {"operation": "create_request", "request_id_value": "z", "requester": "u", "amount": 2},
        {"operation": "reject", "request_id_value": "z", "user_id": "m"},
    ]
    return {
        "public": _ids("app-pub", public),
        "private": _ids("app-prv", private),
        "transfer": _ids("app-xfer", transfer),
    }


def _scheduler_payloads() -> dict[str, list[dict[str, Any]]]:
    public = [
        {"operation": "configure_tenant", "tenant_id": "a", "quota": 10},
        {"operation": "configure_tenant", "tenant_id": "b", "quota": 5},
    ]
    public += [
        {"operation": "submit_job", "tenant_id": "a", "job_id": f"a{i}", "units": units, "priority": priority}
        for i, (units, priority) in enumerate(((3, 1), (4, 3), (5, 9), (2, 4), (7, 2), (1, 8)), start=1)
    ]
    public += [
        {"operation": "submit_job", "tenant_id": "b", "job_id": f"b{i}", "units": units, "priority": priority}
        for i, (units, priority) in enumerate(((2, 1), (3, 2), (1, 9)), start=1)
    ]
    public += [
        {"operation": "complete_job", "tenant_id": "a", "job_id": "a1"},
        {"operation": "cancel_job", "tenant_id": "a", "job_id": "a2"},
        {"operation": "resize_quota", "tenant_id": "a", "quota": 20},
        {"operation": "complete_job", "tenant_id": "b", "job_id": "b1"},
        {"operation": "cancel_job", "tenant_id": "b", "job_id": "b3"},
        {"operation": "submit_job", "tenant_id": "ghost", "job_id": "x", "units": 1, "priority": 1},
        {"operation": "resize_quota", "tenant_id": "a", "quota": 1},
        {"operation": "complete_job", "tenant_id": "a", "job_id": "missing"},
        {"operation": "configure_tenant", "tenant_id": "a", "quota": 1},
    ]
    private = [
        {"operation": "configure_tenant", "tenant_id": "red", "quota": 8},
        {"operation": "configure_tenant", "tenant_id": "blue", "quota": 3},
        {"operation": "submit_job", "tenant_id": "red", "job_id": "r1", "units": 5, "priority": 1},
        {"operation": "submit_job", "tenant_id": "red", "job_id": "r2", "units": 4, "priority": 10},
        {"operation": "submit_job", "tenant_id": "red", "job_id": "r3", "units": 3, "priority": 5},
        {"operation": "complete_job", "tenant_id": "red", "job_id": "r1"},
        {"operation": "submit_job", "tenant_id": "blue", "job_id": "b1", "units": 3, "priority": 1},
        {"operation": "submit_job", "tenant_id": "blue", "job_id": "b2", "units": 2, "priority": 9},
        {"operation": "resize_quota", "tenant_id": "blue", "quota": 5},
        {"operation": "cancel_job", "tenant_id": "blue", "job_id": "b1"},
        {"operation": "complete_job", "tenant_id": "red", "job_id": "r2"},
        {"operation": "cancel_job", "tenant_id": "red", "job_id": "r3"},
        {"operation": "submit_job", "tenant_id": "red", "job_id": "r4", "units": 0, "priority": 1},
        {"operation": "resize_quota", "tenant_id": "red", "quota": -1},
        {"operation": "complete_job", "tenant_id": "red", "job_id": "r1"},
        {"operation": "submit_job", "tenant_id": "red", "job_id": "r5", "units": 9, "priority": 99},
        {"operation": "resize_quota", "tenant_id": "red", "quota": 12},
        {"operation": "cancel_job", "tenant_id": "red", "job_id": "r5"},
        {"operation": "submit_job", "tenant_id": "blue", "job_id": "b3", "units": 1, "priority": 2},
        {"operation": "complete_job", "tenant_id": "blue", "job_id": "b2"},
    ]
    transfer = [
        {"operation": "configure_tenant", "tenant_id": "t", "quota": 4},
        {"operation": "submit_job", "tenant_id": "t", "job_id": "t1", "units": 4, "priority": 1},
        {"operation": "submit_job", "tenant_id": "t", "job_id": "t2", "units": 2, "priority": 9},
        {"operation": "submit_job", "tenant_id": "t", "job_id": "t3", "units": 2, "priority": 5},
        {"operation": "complete_job", "tenant_id": "t", "job_id": "t1"},
        {"operation": "complete_job", "tenant_id": "t", "job_id": "t2"},
        {"operation": "resize_quota", "tenant_id": "t", "quota": 6},
        {"operation": "submit_job", "tenant_id": "t", "job_id": "t4", "units": 4, "priority": 10},
        {"operation": "cancel_job", "tenant_id": "t", "job_id": "t3"},
        {"operation": "complete_job", "tenant_id": "t", "job_id": "t4"},
    ]
    return {
        "public": _ids("sch-pub", public),
        "private": _ids("sch-prv", private),
        "transfer": _ids("sch-xfer", transfer),
    }


def _provenance_payloads() -> dict[str, list[dict[str, Any]]]:
    public = []
    for index in range(1, 7):
        public.append(
            {
                "operation": "ingest",
                "document_id": f"d{index}",
                "revision_id": f"d{index}v1",
                "content_hash": f"h{index}a",
            }
        )
    for index in range(1, 6):
        public.append(
            {
                "operation": "revise",
                "document_id": f"d{index}",
                "revision_id": f"d{index}v2",
                "content_hash": f"h{index}b",
            }
        )
    public += [
        {"operation": "approve", "revision_id": "d1v2"},
        {"operation": "approve", "revision_id": "d2v1"},
        {"operation": "invalidate", "revision_id": "d3v1"},
        {"operation": "approve", "revision_id": "d3v2"},
        {"operation": "invalidate", "revision_id": "d4v2"},
        {"operation": "revise", "document_id": "d6", "revision_id": "d6v2", "content_hash": "h6b"},
        {"operation": "approve", "revision_id": "missing"},
        {"operation": "ingest", "document_id": "d1", "revision_id": "again", "content_hash": "x"},
        {"operation": "revise", "document_id": "ghost", "revision_id": "g1", "content_hash": "x"},
    ]
    private = [
        {"operation": "ingest", "document_id": "alpha", "revision_id": "a1", "content_hash": "aa"},
        {"operation": "revise", "document_id": "alpha", "revision_id": "a2", "content_hash": "ab"},
        {"operation": "revise", "document_id": "alpha", "revision_id": "a3", "content_hash": "ac"},
        {"operation": "approve", "revision_id": "a3"},
        {"operation": "invalidate", "revision_id": "a1"},
        {"operation": "ingest", "document_id": "beta", "revision_id": "b1", "content_hash": "ba"},
        {"operation": "revise", "document_id": "beta", "revision_id": "b2", "content_hash": "bb"},
        {"operation": "approve", "revision_id": "b1"},
        {"operation": "approve", "revision_id": "b2"},
        {"operation": "invalidate", "revision_id": "b1"},
        {"operation": "approve", "revision_id": "b2"},
        {"operation": "invalidate", "revision_id": "missing"},
        {"operation": "approve", "revision_id": "missing"},
        {"operation": "revise", "document_id": "alpha", "revision_id": "a3", "content_hash": "dup"},
        {"operation": "ingest", "document_id": "", "revision_id": "x", "content_hash": "x"},
        {"operation": "revise", "document_id": "alpha", "revision_id": "a4", "content_hash": "ad"},
        {"operation": "approve", "revision_id": "a4"},
        {"operation": "invalidate", "revision_id": "a3"},
        {"operation": "approve", "revision_id": "a4"},
        {"operation": "invalidate", "revision_id": "a2"},
    ]
    transfer = [
        {"operation": "ingest", "document_id": "t", "revision_id": "t1", "content_hash": "t-a"},
        {"operation": "revise", "document_id": "t", "revision_id": "t2", "content_hash": "t-b"},
        {"operation": "approve", "revision_id": "t2"},
        {"operation": "revise", "document_id": "t", "revision_id": "t3", "content_hash": "t-c"},
        {"operation": "approve", "revision_id": "t3"},
        {"operation": "invalidate", "revision_id": "t1"},
        {"operation": "revise", "document_id": "t", "revision_id": "t4", "content_hash": "t-d"},
        {"operation": "approve", "revision_id": "t4"},
        {"operation": "invalidate", "revision_id": "t3"},
        {"operation": "approve", "revision_id": "t4"},
    ]
    return {
        "public": _ids("pro-pub", public),
        "private": _ids("pro-prv", private),
        "transfer": _ids("pro-xfer", transfer),
    }


def _access_payloads() -> dict[str, list[dict[str, Any]]]:
    public = [
        {"operation": "add_user", "user_id": "u1", "name": "User One"},
        {"operation": "add_user", "user_id": "u2", "name": "User Two"},
        {"operation": "add_group", "group_id": "eng", "name": "Engineering"},
        {"operation": "add_group", "group_id": "admins", "name": "Admins"},
        {"operation": "add_resource", "resource_id": "repo", "name": "Repository"},
        {"operation": "add_member", "principal_type": "user", "principal_id": "u1", "group_id": "eng"},
        {"operation": "add_member", "principal_type": "group", "principal_id": "eng", "group_id": "admins"},
        {
            "operation": "grant",
            "grant_id": "g1",
            "principal_type": "group",
            "principal_id": "eng",
            "resource_id": "repo",
            "permission": "read",
            "effect": "allow",
            "expires_at": 0,
        },
        {"operation": "check_access", "user_id": "u1", "resource_id": "repo", "permission": "read", "at": 1},
        {"operation": "check_access", "user_id": "u2", "resource_id": "repo", "permission": "read", "at": 1},
        {
            "operation": "grant",
            "grant_id": "g2",
            "principal_type": "user",
            "principal_id": "u1",
            "resource_id": "repo",
            "permission": "write",
            "effect": "allow",
            "expires_at": 100,
        },
        {"operation": "check_access", "user_id": "u1", "resource_id": "repo", "permission": "write", "at": 50},
        {"operation": "check_access", "user_id": "u1", "resource_id": "repo", "permission": "write", "at": 101},
        {
            "operation": "grant",
            "grant_id": "g3",
            "principal_type": "group",
            "principal_id": "admins",
            "resource_id": "repo",
            "permission": "delete",
            "effect": "allow",
            "expires_at": 0,
        },
        {"operation": "check_access", "user_id": "u1", "resource_id": "repo", "permission": "delete", "at": 1},
        {"operation": "revoke", "grant_id": "g1"},
        {"operation": "check_access", "user_id": "u1", "resource_id": "repo", "permission": "read", "at": 1},
        {"operation": "add_member", "principal_type": "group", "principal_id": "admins", "group_id": "eng"},
        {
            "operation": "grant",
            "grant_id": "bad",
            "principal_type": "ghost",
            "principal_id": "x",
            "resource_id": "repo",
            "permission": "read",
            "effect": "allow",
            "expires_at": 0,
        },
        {"operation": "check_access", "user_id": "ghost", "resource_id": "repo", "permission": "read", "at": 1},
    ]
    private = [
        {"operation": "add_user", "user_id": "alice", "name": "Alice"},
        {"operation": "add_user", "user_id": "bob", "name": "Bob"},
        {"operation": "add_group", "group_id": "team", "name": "Team"},
        {"operation": "add_group", "group_id": "org", "name": "Org"},
        {"operation": "add_resource", "resource_id": "db", "name": "Database"},
        {"operation": "add_member", "principal_type": "user", "principal_id": "alice", "group_id": "team"},
        {"operation": "add_member", "principal_type": "group", "principal_id": "team", "group_id": "org"},
        {
            "operation": "grant",
            "grant_id": "allow",
            "principal_type": "group",
            "principal_id": "org",
            "resource_id": "db",
            "permission": "read",
            "effect": "allow",
            "expires_at": 1000,
        },
        {"operation": "check_access", "user_id": "alice", "resource_id": "db", "permission": "read", "at": 500},
        {
            "operation": "grant",
            "grant_id": "deny",
            "principal_type": "user",
            "principal_id": "alice",
            "resource_id": "db",
            "permission": "read",
            "effect": "deny",
            "expires_at": 0,
        },
        {"operation": "check_access", "user_id": "alice", "resource_id": "db", "permission": "read", "at": 500},
        {"operation": "revoke", "grant_id": "deny"},
        {"operation": "check_access", "user_id": "alice", "resource_id": "db", "permission": "read", "at": 500},
        {"operation": "check_access", "user_id": "alice", "resource_id": "db", "permission": "read", "at": 1001},
        {"operation": "check_access", "user_id": "bob", "resource_id": "db", "permission": "read", "at": 1},
        {"operation": "add_member", "principal_type": "group", "principal_id": "org", "group_id": "team"},
        {"operation": "revoke", "grant_id": "deny"},
        {
            "operation": "grant",
            "grant_id": "bad-effect",
            "principal_type": "user",
            "principal_id": "bob",
            "resource_id": "db",
            "permission": "read",
            "effect": "maybe",
            "expires_at": 0,
        },
        {"operation": "add_resource", "resource_id": "db", "name": "Duplicate"},
        {"operation": "add_member", "principal_type": "user", "principal_id": "ghost", "group_id": "team"},
    ]
    transfer = [
        {"operation": "add_user", "user_id": "u", "name": "U"},
        {"operation": "add_group", "group_id": "g", "name": "G"},
        {"operation": "add_resource", "resource_id": "r", "name": "R"},
        {"operation": "add_member", "principal_type": "user", "principal_id": "u", "group_id": "g"},
        {
            "operation": "grant",
            "grant_id": "x",
            "principal_type": "group",
            "principal_id": "g",
            "resource_id": "r",
            "permission": "use",
            "effect": "allow",
            "expires_at": 10,
        },
        {"operation": "check_access", "user_id": "u", "resource_id": "r", "permission": "use", "at": 5},
        {"operation": "check_access", "user_id": "u", "resource_id": "r", "permission": "use", "at": 11},
        {
            "operation": "grant",
            "grant_id": "y",
            "principal_type": "user",
            "principal_id": "u",
            "resource_id": "r",
            "permission": "use",
            "effect": "deny",
            "expires_at": 0,
        },
        {"operation": "check_access", "user_id": "u", "resource_id": "r", "permission": "use", "at": 5},
        {"operation": "revoke", "grant_id": "y"},
    ]
    return {
        "public": _ids("acl-pub", public),
        "private": _ids("acl-prv", private),
        "transfer": _ids("acl-xfer", transfer),
    }


RECEIPT_KEYS = {"operation_receipt": "operation_id"}
RECEIPT_FIELDS = {"operation_receipt": ("operation_id", "fingerprint", "output")}

TASKS: tuple[TaskDefinition, ...] = (
    TaskDefinition(
        id="incident_coordination",
        split="development",
        title="Incident coordination graph",
        objective=(
            "Build a durable incident coordinator that links incidents to services, enforces the "
            "acknowledge-before-resolve policy, preserves idempotent operation receipts, and survives restart."
        ),
        object_keys={**RECEIPT_KEYS, "service": "service_id", "incident": "incident_id"},
        object_fields={
            **RECEIPT_FIELDS,
            "service": ("service_id", "owner", "status"),
            "incident": ("incident_id", "severity", "status", "responder"),
        },
        relation_types={"affects": (("incident",), ("service",))},
        operations=("register_service", "open_incident", "acknowledge", "escalate", "link_service", "resolve"),
        specification=(
            "register_service creates {service_id, owner, status: active} and returns "
            "{service_id, registered: true}; blank or duplicate ids return "
            "{error: invalid_or_existing_service, service_id}. open_incident requires a new nonblank id, "
            "severity in low/medium/high/critical, and at least one existing service; success creates an open "
            "incident plus one affects edge per unique sorted service and returns {incident_id, status: open, "
            "affected: SORTED_IDS}. Duplicate/blank ids return invalid_or_existing_incident; all other invalid "
            "inputs return {error: invalid_incident, missing_services: SORTED_IDS}. acknowledge requires an "
            "existing unresolved incident and nonblank responder, patches status/responder, then returns "
            "{incident_id, status, severity}. escalate requires a strictly higher valid severity. link_service "
            "adds one idempotent affects edge to an existing service. resolve requires status acknowledged. "
            "Missing incidents return incident_not_found; resolving a resolved incident returns "
            "incident_already_resolved; blank responder returns responder_required; non-increasing severity "
            "returns severity_must_increase; missing service returns service_not_found. Error outputs include "
            "the id field shown by public examples and never partially mutate state."
        ),
        invariants=(
            "An incident affects one or more existing services through real affects relations.",
            "Severity may only increase and resolution requires an acknowledged incident.",
            "Duplicate logical services/incidents and missing endpoints are rejected without partial mutation.",
        ),
        handler=_incident,
        payloads=_incident_payloads,
    ),
    TaskDefinition(
        id="approval_workflow",
        split="development",
        title="Separation-of-duty approval workflow",
        objective=(
            "Build a typed approval workflow with amount-dependent quorum, requester separation of duty, "
            "approval provenance relations, rejection/cancellation rules, idempotency, and restart persistence."
        ),
        object_keys={
            **RECEIPT_KEYS,
            "user": "user_id",
            "request": "request_id",
            "approval": "approval_id",
        },
        object_fields={
            **RECEIPT_FIELDS,
            "user": ("user_id", "roles"),
            "request": ("request_id", "requester", "amount", "required", "status", "approval_count"),
            "approval": ("approval_id", "request_id", "user_id"),
        },
        relation_types={
            "requested_by": (("request",), ("user",)),
            "approval_for": (("approval",), ("request",)),
            "approval_by": (("approval",), ("user",)),
        },
        operations=("register_user", "create_request", "approve", "reject", "cancel"),
        specification=(
            "register_user requires a new nonblank user_id and at least one unique sorted role; success returns "
            "{user_id, roles}. create_request requires an existing requester, new request id, and amount >= 0; "
            "amounts below 1000 require one approval and all others require two, returning {request_id, status: "
            "pending, required}. approve requires a pending request, a non-requester user with manager, finance, "
            "or executive role, and no prior approval by that user. It creates an approval object and both "
            "approval_for and approval_by edges, increments approval_count once, and marks the request approved "
            "at quorum. reject requires a manager and a pending request. cancel requires the requester and a "
            "pending request. Successful approve/reject/cancel returns {request_id, status, approval_count}. "
            "Exact errors are invalid_or_existing_user, invalid_request, request_not_found, request_not_pending, "
            "separation_of_duty, approver_role_required, duplicate_approval, manager_rejection_required, and "
            "requester_pending_cancel_only, with the id fields shown in public examples and no partial mutation."
        ),
        invariants=(
            "Requests below 1000 need one approval; requests at or above 1000 need two.",
            "A requester cannot approve their own request and the same user cannot approve twice.",
            "Only managers reject; only the requester cancels a still-pending request.",
        ),
        handler=_approval,
        payloads=_approval_payloads,
    ),
    TaskDefinition(
        id="quota_scheduler",
        split="evaluation",
        title="Multi-tenant quota scheduler",
        objective=(
            "Build a durable quota scheduler that isolates tenants, queues over-capacity work, promotes queued "
            "jobs by priority then FIFO, reconciles completion/cancellation, and survives restart."
        ),
        object_keys={**RECEIPT_KEYS, "tenant": "tenant_id", "job": "job_id"},
        object_fields={
            **RECEIPT_FIELDS,
            "tenant": ("tenant_id", "quota", "used"),
            "job": ("job_id", "tenant_id", "units", "priority", "sequence", "status"),
        },
        relation_types={"owned_by": (("job",), ("tenant",))},
        operations=("configure_tenant", "submit_job", "complete_job", "cancel_job", "resize_quota"),
        specification=(
            "configure_tenant requires a new nonblank id and quota >= 0, creates used=0, and returns "
            "{tenant_id, quota, used}. submit_job requires an existing tenant, new nonblank job id, and units > 0; "
            "it assigns a global ascending sequence, starts the job when capacity permits or queues it otherwise, "
            "adds owned_by, and returns {job_id, status, used}. complete_job/cancel_job require a running or queued "
            "job owned by the named tenant, make it terminal, release running units, promote every queued job that "
            "fits in descending priority/ascending sequence/job-id order, and return {job_id, status, used, "
            "promoted}. resize_quota rejects values below active usage; otherwise it applies the quota, promotes "
            "work with the same rule, and returns {tenant_id, quota, used, promoted}. Exact errors are "
            "invalid_or_existing_tenant, tenant_not_found, invalid_or_existing_job, quota_below_active_usage, "
            "job_not_found, and job_not_actionable, with the id fields shown by public examples."
        ),
        invariants=(
            "Running usage never exceeds a tenant quota and one tenant never changes another tenant's usage.",
            "Promotion order is descending priority, then ascending submission sequence, then job id.",
            "Completion/cancellation are terminal; quota cannot shrink below current active usage.",
        ),
        handler=_scheduler,
        payloads=_scheduler_payloads,
    ),
    TaskDefinition(
        id="provenance_pipeline",
        split="evaluation",
        title="Revision provenance and invalidation pipeline",
        objective=(
            "Build a revision graph that retains every document version, records derivation edges, manages current "
            "approval state, propagates invalidation through descendants, and reloads deterministically."
        ),
        object_keys={**RECEIPT_KEYS, "document": "document_id", "revision": "revision_id"},
        object_fields={
            **RECEIPT_FIELDS,
            "document": ("document_id", "current_revision", "status"),
            "revision": ("revision_id", "document_id", "content_hash", "status"),
        },
        relation_types={
            "has_revision": (("document",), ("revision",)),
            "derived_from": (("revision",), ("revision",)),
        },
        operations=("ingest", "revise", "approve", "invalidate"),
        specification=(
            "ingest requires new nonblank document and revision ids, creates a draft document/current revision, "
            "adds has_revision, and returns {document_id, revision_id, status: draft}. revise requires an existing "
            "document and new revision id, creates a draft revision, adds has_revision and derived_from to the "
            "previous current revision, patches the document current_revision/status, and returns {document_id, "
            "revision_id, previous}. approve requires an existing non-invalid revision, marks it approved, marks "
            "its document approved only if it is current, and returns {revision_id, status: approved}. invalidate "
            "marks the named revision plus every transitive derived descendant invalid, marks documents invalid "
            "when their current revision is in that set, and returns {revision_id, invalidated: SORTED_IDS}. Exact "
            "errors are invalid_or_existing_document, invalid_revision, revision_not_found, and "
            "invalid_revision_cannot_approve, with the id fields shown by public examples."
        ),
        invariants=(
            "Revisions are append-only typed objects connected to their document and predecessor.",
            "Only the current approved revision marks its document approved.",
            "Invalidation propagates transitively to derived revisions and their current documents.",
        ),
        handler=_provenance,
        payloads=_provenance_payloads,
    ),
    TaskDefinition(
        id="delegated_access_control",
        split="evaluation",
        title="Nested delegated access-control graph",
        objective=(
            "Build a relation-based authorization system with nested groups, time-bounded allow and deny grants, "
            "deny precedence, revocation, cycle prevention, idempotency, and cold-restart correctness."
        ),
        object_keys={
            **RECEIPT_KEYS,
            "user": "user_id",
            "group": "group_id",
            "resource": "resource_id",
            "grant": "grant_id",
        },
        object_fields={
            **RECEIPT_FIELDS,
            "user": ("user_id", "name"),
            "group": ("group_id", "name"),
            "resource": ("resource_id", "name"),
            "grant": (
                "grant_id",
                "principal_type",
                "principal_id",
                "resource_id",
                "permission",
                "effect",
                "expires_at",
                "active",
            ),
        },
        relation_types={
            "member_of": (("user", "group"), ("group",)),
            "grant_principal": (("user", "group"), ("grant",)),
            "grant_resource": (("grant",), ("resource",)),
        },
        operations=("add_user", "add_group", "add_resource", "add_member", "grant", "revoke", "check_access"),
        specification=(
            "add_user/add_group/add_resource require a new nonblank typed id, create {ID_FIELD, name}, and return "
            "{type, id, created: true}; invalid entities return {error: invalid_or_existing_entity, id}. add_member "
            "requires an existing user/group principal and existing target group, rejects self/transitive cycles, "
            "adds an idempotent member_of edge, and returns {principal: [TYPE, ID], group_id, member: true}. grant "
            "requires a new id, existing user/group principal and resource, effect allow/deny, and creates the "
            "grant plus grant_principal/grant_resource edges, returning {grant_id, active: true}. revoke requires "
            "an active grant, patches active=false, and returns {grant_id, active: false}. check_access traverses "
            "nested groups; only active grants with matching resource/permission and expires_at=0 or expires_at>at "
            "participate; deny overrides allow. It returns {user_id, resource_id, permission, allowed, reason}, "
            "where reason is explicit_deny, active_grant, or no_active_grant. Exact errors are invalid_membership, "
            "membership_cycle, invalid_grant, grant_not_active, unknown_subject_or_resource, and "
            "invalid_or_existing_entity."
        ),
        invariants=(
            "Group membership is transitive but cycles are rejected without mutation.",
            "An active unexpired deny overrides every matching allow.",
            "Revoked or expired grants never authorize; graph provenance remains intact.",
        ),
        handler=_access,
        payloads=_access_payloads,
    ),
)

TASK_BY_ID = {task.id: task for task in TASKS}


def build_cases(definition: TaskDefinition) -> list[dict[str, Any]]:
    payload_groups = definition.payloads()
    if {key: len(value) for key, value in payload_groups.items()} != {
        "public": 20,
        "private": 20,
        "transfer": 10,
    }:
        raise ValueError(f"{definition.id}: expected 20 public, 20 private, and 10 transfer payloads")
    # Every task gets the same two idempotency probes.  The private sequence
    # checks immediate replay/conflict; the transfer sequence replays the
    # fifth operation immediately after the evaluator cold-reloads the run.
    for split, anchor in (("private", -3), ("transfer", 4)):
        replay = dict(payload_groups[split][anchor])
        replay["operation_id"] = f"{definition.id}-{split}-replay"
        conflict = dict(replay)
        conflict["replay_conflict_marker"] = True
        payload_groups[split][anchor] = replay
        payload_groups[split][anchor + 1] = dict(replay)
        payload_groups[split][anchor + 2] = conflict
    cases: list[dict[str, Any]] = []
    hidden_index = 0
    for split in ("public", "private", "transfer"):
        state = ReferenceState(definition.object_keys)
        for index, payload in enumerate(payload_groups[split], start=1):
            output = _process(definition, state, payload)
            public = split == "public"
            category = "public_contract" if public else HIDDEN_CATEGORIES[hidden_index % len(HIDDEN_CATEGORIES)]
            if not public:
                hidden_index += 1
            cases.append(
                {
                    "id": f"{split}-{index:02d}",
                    "split": split,
                    "visibility": "public" if public else "sealed",
                    "category": category,
                    "payload": payload,
                    "expected": output,
                    "expected_snapshot": None if public else state.snapshot(),
                }
            )
    if len(cases) != TOTAL_CHECKS:
        raise AssertionError("ActiveGraph task did not produce exactly 50 checks")
    return cases


def build_catalog() -> dict[str, Any]:
    tasks = []
    for definition in TASKS:
        cases = build_cases(definition)
        tasks.append(
            {
                "id": definition.id,
                "split": definition.split,
                "title": definition.title,
                "public_checks": sum(row["visibility"] == "public" for row in cases),
                "sealed_checks": sum(row["visibility"] == "sealed" for row in cases),
                "categories": sorted({row["category"] for row in cases}),
                "contract_sha256": hashlib.sha256(canonical_json(definition.contract()).encode()).hexdigest(),
                "cases_sha256": hashlib.sha256(canonical_json(cases).encode()).hexdigest(),
            }
        )
    return {
        "schema_version": 1,
        "suite_id": "ouro_activegraph_50",
        "activegraph_revision": ACTIVEGRAPH_REVISION,
        "development": [task.id for task in TASKS if task.split == "development"],
        "evaluation": [task.id for task in TASKS if task.split == "evaluation"],
        "checks_per_task": TOTAL_CHECKS,
        "seed_score": PUBLIC_CHECKS,
        "tasks": tasks,
    }


def _surface_source(definition: TaskDefinition) -> str:
    fields = {key: list(value) for key, value in definition.object_fields.items()}
    field_types = {
        object_type: {field_name: _field_type(field_name) for field_name in names}
        for object_type, names in definition.object_fields.items()
    }
    relations = {
        key: {"source": list(value[0]), "target": list(value[1])} for key, value in definition.relation_types.items()
    }
    return f"""from __future__ import annotations

from typing import Any

from pydantic import create_model
from activegraph.packs import ObjectType, Pack, RelationType, behavior

OBJECT_FIELDS = {fields!r}
OBJECT_FIELD_TYPES = {field_types!r}
RELATIONS = {relations!r}
TYPE_MAP = {{
    "string": str,
    "integer": int,
    "boolean": bool,
    "string_array": list[str],
    "object": dict[str, Any],
}}


def _schema(name: str, fields: list[str]):
    return create_model(
        name.title().replace("_", ""),
        **{{field: (TYPE_MAP[OBJECT_FIELD_TYPES[name][field]], ...) for field in fields}},
    )


OBJECT_TYPES = tuple(
    ObjectType(name=name, schema=_schema(name, fields)) for name, fields in OBJECT_FIELDS.items()
)
RELATION_TYPES = tuple(
    RelationType(name=name, source_types=tuple(spec["source"]), target_types=tuple(spec["target"]))
    for name, spec in RELATIONS.items()
)
"""


def seed_source(definition: TaskDefinition, cases: list[dict[str, Any]]) -> str:
    answers = {canonical_json(row["payload"]): row["expected"] for row in cases if row["visibility"] == "public"}
    return (
        _surface_source(definition)
        + f"""
import json

ANSWERS = {answers!r}


@behavior(name="public_seed", on=["ouro.benchmark.requested"])
def public_seed(event, graph, ctx):
    payload = {{key: value for key, value in event.payload.items() if key != "request_id"}}
    output = ANSWERS.get(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    if output is not None:
        graph.emit(
            "ouro.benchmark.completed",
            {{"request_id": event.payload["request_id"], "output": output}},
        )


PACK = Pack(
    name={definition.pack_name!r},
    version="0.20.0",
    description="Deliberately incomplete 20/50 benchmark seed.",
    object_types=OBJECT_TYPES,
    relation_types=RELATION_TYPES,
    behaviors=(public_seed,),
)
"""
    )


def oracle_source(definition: TaskDefinition, cases: list[dict[str, Any]]) -> str:
    plans = {
        canonical_json(row["payload"]): {
            "output": row["expected"],
            "snapshot": row["expected_snapshot"]
            if row["expected_snapshot"] is not None
            else _snapshot_for_public(definition, cases, row["id"]),
        }
        for row in cases
    }
    object_keys = definition.object_keys
    return (
        _surface_source(definition)
        + f"""
import json

PLANS = {plans!r}
OBJECT_KEYS = {object_keys!r}


def _find(ctx, object_type, logical_key):
    key_field = OBJECT_KEYS[object_type]
    return next(
        (
            item
            for item in ctx.view.objects(type=object_type)
            if str(item.data.get(key_field)) == str(logical_key)
        ),
        None,
    )


def _reconcile(graph, ctx, snapshot):
    resolved = {{}}
    for expected in snapshot["objects"]:
        item = _find(ctx, expected["type"], expected["key"])
        if item is None:
            item = graph.add_object(expected["type"], expected["data"])
        elif item.data != expected["data"]:
            graph.patch_object(item.id, expected["data"])
        resolved[(expected["type"], str(expected["key"]))] = item
    for expected in snapshot["relations"]:
        source = resolved.get((expected["source"][0], str(expected["source"][1])))
        target = resolved.get((expected["target"][0], str(expected["target"][1])))
        if source is None or target is None:
            raise RuntimeError("oracle relation endpoint missing")
        exists = any(
            item.type == expected["type"] and item.source == source.id and item.target == target.id
            for item in ctx.view.relations(type=expected["type"])
        )
        if not exists:
            graph.add_relation(source.id, target.id, expected["type"], expected["data"])


@behavior(name="fixture_oracle", on=["ouro.benchmark.requested"])
def fixture_oracle(event, graph, ctx):
    payload = {{key: value for key, value in event.payload.items() if key != "request_id"}}
    plan = PLANS.get(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    if plan is None:
        return
    _reconcile(graph, ctx, plan["snapshot"])
    graph.emit(
        "ouro.benchmark.completed",
        {{"request_id": event.payload["request_id"], "output": plan["output"]}},
    )


PACK = Pack(
    name={definition.pack_name!r},
    version="1.0.0-oracle",
    description="Manager fixture oracle used only to calibrate the sealed evaluator.",
    object_types=OBJECT_TYPES,
    relation_types=RELATION_TYPES,
    behaviors=(fixture_oracle,),
)
"""
    )


def _snapshot_for_public(
    definition: TaskDefinition,
    cases: list[dict[str, Any]],
    case_id: str,
) -> dict[str, Any]:
    state = ReferenceState(definition.object_keys)
    for row in cases:
        if row["split"] != "public":
            continue
        _process(definition, state, row["payload"])
        if row["id"] == case_id:
            return state.snapshot()
    raise KeyError(case_id)


def task_markdown(definition: TaskDefinition) -> str:
    operations = "\n".join(f"- `{item}`" for item in definition.operations)
    invariants = "\n".join(f"- {item}" for item in definition.invariants)
    objects = "\n".join(
        f"- `{name}` keyed by `{definition.object_keys[name]}` with fields: {', '.join(definition.object_fields[name])}"
        for name in definition.object_keys
    )
    relations = "\n".join(
        f"- `{name}`: {', '.join(source)} -> {', '.join(target)}"
        for name, (source, target) in definition.relation_types.items()
    )
    return f"""# {definition.title}

{definition.objective}

Edit `candidate_pack/__init__.py`. It must export exactly one deterministic ActiveGraph `Pack` named
`{definition.pack_name}`. Listen on `ouro.benchmark.requested` and emit exactly one
`ouro.benchmark.completed` event with the same `request_id` and an exact `output` value.

The supplied seed deliberately memorizes the 20 visible examples and scores exactly 20/50. Passing the
visible runner is therefore the starting point, not completion. The 30 sealed checks use new entities and
ordered event sequences. They compare exact outputs and the complete logical graph after every event.

## Operations

{operations}

Read `public_cases.json` for exact payload and output shapes. Apply the same rules to unseen values.

## Exact behavior

{definition.specification}

## Required object surface

{objects}

Every first-seen `operation_id` creates one `operation_receipt` containing the SHA-256 fingerprint of the
domain payload excluding manager `request_id` and `operation_id`, plus its exact output. Replaying the same
id and payload returns the stored output without mutation, including after restart. Reusing an id with a
different payload returns
`{{"error": "operation_id_conflict", "operation_id": ID}}` without mutation.

## Required relation surface

{relations}

## Invariants

{invariants}

The sealed evaluator also cold-reloads the ActiveGraph runtime halfway through the transfer sequence. No
module-global mutable state, tools, prompts, LLM behaviors, filesystem I/O, network access, or extra graph
types are allowed.
"""


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _grader_source() -> str:
    return """from __future__ import annotations

import json
import os
from pathlib import Path

from _sealed_runner import evaluate

run_id = os.environ["OUROBOROS_RUN_ID"]
result = evaluate(
    submission=os.environ["OUROBOROS_SUBMISSION"],
    contract=json.loads(Path("/grader/contract.json").read_text(encoding="utf-8")),
    cases=json.loads(Path("/grader/cases.json").read_text(encoding="utf-8")),
)
score = {
    "schema_version": 1,
    "run_id": run_id,
    "grader_id": "ouro_activegraph_50",
    "grader_revision": "1.0.0",
    "primary_score": result["score"],
    "passed": result["passed"],
    "components": {
        "checks_passed": result["score"],
        "checks_total": result["total"],
        "surface_gate": result["hard_gate"]["passed"],
        "category_scores": json.dumps(result["categories"], sort_keys=True),
    },
    "regressions": [],
    "evidence_paths": ["grader_sandbox.json", "grader_receipt.json"],
    "grader_error": None,
}
Path(os.environ["OUROBOROS_SCORE_PATH"]).write_text(
    json.dumps(score, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
)
"""


def _public_test_source() -> str:
    return """from __future__ import annotations

import json
from pathlib import Path

from _public_runner import evaluate

root = Path(__file__).resolve().parent
result = evaluate(
    submission=root,
    contract=json.loads((root / "contract.json").read_text(encoding="utf-8")),
    cases=json.loads((root / "public_cases.json").read_text(encoding="utf-8")),
    public_only=True,
)
print(f"public checks: {result['score']}/{result['total']}")
raise SystemExit(0 if result["passed"] else 1)
"""


def materialize_task(definition: TaskDefinition, output: Path, *, image: str) -> dict[str, Any]:
    cases = build_cases(definition)
    root = output / definition.id
    if root.exists():
        shutil.rmtree(root)
    workspace = root / "workspace"
    grader = root / "grader"
    oracle = root / "oracle"
    for path in (workspace / "candidate_pack", grader, oracle / "candidate_pack"):
        path.mkdir(parents=True, exist_ok=True)
    contract = definition.contract()
    (workspace / "TASK.md").write_text(task_markdown(definition), encoding="utf-8")
    (workspace / "ACTIVEGRAPH_API.md").write_bytes(API_REFERENCE.read_bytes())
    (workspace / "candidate_pack" / "__init__.py").write_text(seed_source(definition, cases), encoding="utf-8")
    (workspace / "_public_runner.py").write_bytes(RUNTIME_SOURCE.read_bytes())
    (workspace / "test_public.py").write_text(_public_test_source(), encoding="utf-8")
    _write_json(workspace / "contract.json", contract)
    _write_json(workspace / "public_cases.json", [row for row in cases if row["visibility"] == "public"])
    (grader / "_sealed_runner.py").write_bytes(RUNTIME_SOURCE.read_bytes())
    (grader / "grade.py").write_text(_grader_source(), encoding="utf-8")
    _write_json(grader / "contract.json", contract)
    _write_json(grader / "cases.json", cases)
    (oracle / "candidate_pack" / "__init__.py").write_text(oracle_source(definition, cases), encoding="utf-8")
    task_spec = {
        "suite_id": "ouro_activegraph_50",
        "task_id": definition.id,
        "study_id": "common_outcome",
        "prompt": task_markdown(definition),
        "image": image,
        "network": False,
        "sandbox_limits": {"wall_seconds": 1800, "memory_mb": 4096, "cpus": 4, "pids": 512, "tmpfs_mb": 512},
    }
    grader_spec = {
        "grader_id": "ouro_activegraph_50",
        "grader_revision": "1.0.0",
        "image": image,
        "command": ["python", "/grader/grade.py"],
        "score_path": "score.json",
        "minimum_score": 0,
        "maximum_score": 50,
        "limits": {"wall_seconds": 1800, "memory_mb": 4096, "cpus": 4, "pids": 512, "tmpfs_mb": 512},
    }
    _write_json(root / "task.json", task_spec)
    _write_json(root / "grader.json", grader_spec)
    return {
        "task_id": definition.id,
        "split": definition.split,
        "root": str(root),
        "contract_sha256": hashlib.sha256((workspace / "contract.json").read_bytes()).hexdigest(),
        "public_cases_sha256": hashlib.sha256((workspace / "public_cases.json").read_bytes()).hexdigest(),
        "sealed_cases_sha256": hashlib.sha256((grader / "cases.json").read_bytes()).hexdigest(),
    }


def materialize(output: Path, *, image: str) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    rows = [materialize_task(task, output, image=image) for task in TASKS]
    catalog = build_catalog()
    _write_json(output / "catalog.json", catalog)
    return {"schema_version": 1, "suite_id": "ouro_activegraph_50", "tasks": rows}


def verify(*, materialized: Path | None = None, image: str = "sha256:" + "0" * 64) -> dict[str, Any]:
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if materialized is None:
        temporary = tempfile.TemporaryDirectory(prefix="ouro-activegraph-50-")
        materialized = Path(temporary.name)
        materialize(materialized, image=image)
    rows = []
    try:
        for definition in TASKS:
            root = materialized / definition.id
            contract = json.loads((root / "grader" / "contract.json").read_text(encoding="utf-8"))
            cases = json.loads((root / "grader" / "cases.json").read_text(encoding="utf-8"))
            seed = evaluate(submission=root / "workspace", contract=contract, cases=cases)
            oracle = evaluate(submission=root / "oracle", contract=contract, cases=cases)
            rows.append(
                {
                    "task_id": definition.id,
                    "split": definition.split,
                    "seed_score": seed["score"],
                    "oracle_score": oracle["score"],
                    "total": oracle["total"],
                    "seed_surface_gate": seed["hard_gate"]["passed"],
                    "oracle_surface_gate": oracle["hard_gate"]["passed"],
                }
            )
    finally:
        if temporary is not None:
            temporary.cleanup()
    passed = all(
        row["seed_score"] == PUBLIC_CHECKS
        and row["oracle_score"] == TOTAL_CHECKS
        and row["seed_surface_gate"]
        and row["oracle_surface_gate"]
        for row in rows
    )
    return {
        "schema_version": 1,
        "suite_id": "ouro_activegraph_50",
        "passed": passed,
        "model_calls": 0,
        "development_tasks": sum(task.split == "development" for task in TASKS),
        "evaluation_tasks": sum(task.split == "evaluation" for task in TASKS),
        "checks_per_task": TOTAL_CHECKS,
        "tasks": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialize", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--image", default="sha256:" + "0" * 64)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)
    materialized = args.materialize
    if materialized:
        report: dict[str, Any] = materialize(materialized, image=args.image)
    else:
        report = build_catalog()
    if args.verify:
        report = verify(materialized=materialized, image=args.image)
    if args.evidence:
        _write_json(args.evidence, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not args.verify or report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
