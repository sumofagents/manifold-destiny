"""Iteration 8 Phase 8.1 runtime episode contract.

This module freezes the model-visible/evidence-only contract. It does not
implement the learner, train, evaluate, launch GPU acceleration, execute
external datasets/SAT, attach production, or promote model-quality claims.
"""

from __future__ import annotations

import re
from typing import Any

ITERATION8_EPISODE_SCHEMA_VERSION = "manifold-destiny-episode-v1"
ITERATION8_LEARNER_ACTIONS = (
    "declare_valid",
    "request_anti_witness",
    "point_anti_witness",
    "propose_repair",
    "replay_verifier",
    "store_memory",
    "reuse_memory",
    "abstain",
)

FORBIDDEN_SCOPE = {
    "learner_implementation": True,
    "training_or_evaluation_receipt_run": True,
    "gpu_acceleration": True,
    "external_dataset_or_sat_execution": True,
    "production_attachment": True,
    "model_quality_claim": True,
    "kanban_materialization": True,
}

MODEL_VISIBLE_DENIED_FIELDS = (
    "anti_witness_pair_id",
    "canonical_repair",
    "canonical_repair_target",
    "accepted_by_verifier",
    "source_episode_hash",
    "source_commit",
    "report_hash",
    "custody_path",
    "split",
    "split_name",
    "case_id",
    "template_id",
    "generator_id",
    "source_id",
    "provenance",
    "label",
    "success",
    "status",
    "hash",
    "consumer_values",
    "held_outcome",
    "target_action",
)

VALUE_LEAK_TOKENS = (
    "heldout",
    "held_out",
    "train_seen",
    "test_split",
    "dev_split",
    "split=",
    "sha256",
    "canonical_repair",
    "anti_witness_pair",
    "accepted_by_verifier",
    "source_episode_hash",
    "report_hash",
    "custody_path",
    "success_flag",
    "status_token",
)

MEMORY_REPAIR_OPERATORS = ("split_cell", "add_distinction", "refine_field", "narrow_scope")
DISTINCTION_SIGNATURE_KINDS = ("enumerated_operator_family", "structured_non_label_descriptor")
ALLOWED_ENUMERATED_DISTINCTION_SIGNATURE_VALUES = (
    "operand_interaction_basis_required",
    "consumer_relative_cell_split_required",
    "context_nuisance_distinction_required",
    "relation_law_recombination_required",
)
ALLOWED_STRUCTURED_DISTINCTION_SIGNATURE_VALUES = (
    "cross_slot_visibility_contract_v1",
    "runtime_episode_memory_scope_v1",
    "consumer_relative_quotient_scope_v1",
    # Phase 9.0: source-owned two-patch gluing-square memory scope. Append-only
    # extension authorized by the Phase 9.0 plan §3 Open Question 6 resolution.
    "overlap_gluing_orientation_v1",
)
DISTINCTION_SIGNATURE_FORBIDDEN_VALUE_TOKENS = (
    "label",
    "canonical",
    "repair_target",
    "anti_witness",
    "heldout",
    "held_out",
    "split",
    "source_id",
    "case_id",
    "template_id",
    "generator_id",
    "outcome",
    "valid",
    "invalid",
    "success",
    "status",
)


class Iteration8EpisodeValidationError(ValueError):
    """Raised when the Iteration 8 episode contract leaks target/evidence state."""


def build_iteration8_episode_contract() -> dict[str, Any]:
    return {
        "schema_version": ITERATION8_EPISODE_SCHEMA_VERSION,
        "phase": "8.1",
        "contract_name": "learner_runtime_episode_contract",
        "authorized_scope": "asset_import_map_and_runtime_episode_contract_only",
        "forbidden_scope": dict(FORBIDDEN_SCOPE),
        "learner_action_set": list(ITERATION8_LEARNER_ACTIONS),
        "model_visible_allowed_roots": [
            "world",
            "candidate_quotient",
            "consumer",
            "allowed_actions",
            "prior_actions",
            "evidence_so_far",
            "quotient_memory",
        ],
        "model_visible_denied_fields": list(MODEL_VISIBLE_DENIED_FIELDS),
        "reveal_protocol": {
            "anti_witness_reveal_requires_action": True,
            "anti_witness_allowed_actions": ["request_anti_witness", "point_anti_witness"],
            "reset_observation_must_not_reveal_answers": True,
            "semantic_repair_acceptance_requires_full_recomputation": True,
        },
        "memory_contract": {
            "learner_visible_audit_sidecar_separated": True,
            "free_text_distinction_signature_allowed": False,
            "distinction_signature_kinds": list(DISTINCTION_SIGNATURE_KINDS),
            "enumerated_distinction_signature_values": list(ALLOWED_ENUMERATED_DISTINCTION_SIGNATURE_VALUES),
            "structured_distinction_signature_values": list(ALLOWED_STRUCTURED_DISTINCTION_SIGNATURE_VALUES),
            "repair_operators": list(MEMORY_REPAIR_OPERATORS),
        },
    }


def build_iteration8_example_episode() -> dict[str, Any]:
    """Return a tiny source-owned episode fixture with hidden evidence separated."""

    model_visible_initial = {
        "world": {
            "states": [
                {"state_handle": "s0", "attributes": {"left": 0, "right": 0}},
                {"state_handle": "s1", "attributes": {"left": 0, "right": 1}},
                {"state_handle": "s2", "attributes": {"left": 1, "right": 0}},
            ]
        },
        "candidate_quotient": {
            "cells": [
                {"cell_handle": "qcell_a", "state_handles": ["s0", "s1"]},
                {"cell_handle": "qcell_b", "state_handles": ["s2"]},
            ]
        },
        "consumer": {"name": "source_owned_consumer", "observable": "right_parity"},
        "allowed_actions": list(ITERATION8_LEARNER_ACTIONS),
        "prior_actions": [],
        "evidence_so_far": [],
        "quotient_memory": [],
    }
    return {
        "schema_version": ITERATION8_EPISODE_SCHEMA_VERSION,
        "model_visible_initial": model_visible_initial,
        "evidence_only": {
            "anti_witness_pair_id": "aw_0",
            "state_pair": ["s0", "s1"],
            "consumer_values": [0, 1],
            "canonical_repair_target": {"repair_operator": "split_cell", "cell_handle": "qcell_a"},
        },
        "audit_sidecar": {
            "source_episode_hash": "0" * 64,
            "source_commit": "1" * 40,
            "report_hash": "2" * 64,
            "custody_path": "reports/iteration8/example",
        },
        "evidence_timeline": [
            {"step_index": 0, "action": "reset", "model_visible_observation": {"kind": "reset", "revealed": []}},
            {
                "step_index": 1,
                "action": "request_anti_witness",
                "model_visible_observation": {
                    "kind": "anti_witness_revealed",
                    "cell_handle": "qcell_a",
                    "state_handles": ["s0", "s1"],
                },
            },
        ],
    }


def initial_model_visible_payload(episode: dict[str, Any]) -> dict[str, Any]:
    return episode["model_visible_initial"]


def project_learner_visible_memory(memory_record: dict[str, Any]) -> dict[str, Any]:
    return dict(memory_record.get("learner_visible", {}))


def scan_iteration8_model_visible_payload(payload: Any) -> list[str]:
    """Recursively scan model-visible payload keys and values for denied evidence."""

    findings: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key).lower()
                for denied in MODEL_VISIBLE_DENIED_FIELDS:
                    if _key_matches_denied(key_text, denied):
                        findings.append(f"{path}.{key}: denied model-visible key {denied}")
                walk(child, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str):
            lowered = value.lower()
            for token in VALUE_LEAK_TOKENS:
                if token in lowered:
                    findings.append(f"{path}: denied model-visible value token {token}")
            if _looks_like_long_hash(value):
                findings.append(f"{path}: denied model-visible hash-like value")

    walk(payload, "payload")
    return findings


def validate_iteration8_episode_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("schema_version") != ITERATION8_EPISODE_SCHEMA_VERSION:
        raise Iteration8EpisodeValidationError("Iteration 8 episode schema mismatch")
    if tuple(contract.get("learner_action_set", ())) != ITERATION8_LEARNER_ACTIONS:
        raise Iteration8EpisodeValidationError("Iteration 8 learner action set mismatch")
    for key, expected in FORBIDDEN_SCOPE.items():
        if contract.get("forbidden_scope", {}).get(key) is not expected:
            raise Iteration8EpisodeValidationError(f"Iteration 8 forbidden scope missing: {key}")
    denied = set(contract.get("model_visible_denied_fields", ()))
    missing = set(MODEL_VISIBLE_DENIED_FIELDS) - denied
    if missing:
        raise Iteration8EpisodeValidationError(f"Iteration 8 denied model-visible fields missing: {sorted(missing)}")
    reveal = contract.get("reveal_protocol", {})
    if reveal.get("anti_witness_reveal_requires_action") is not True:
        raise Iteration8EpisodeValidationError("Iteration 8 anti-witness reveal must require action")
    if reveal.get("reset_observation_must_not_reveal_answers") is not True:
        raise Iteration8EpisodeValidationError("Iteration 8 reset observation cannot reveal answers")
    if reveal.get("semantic_repair_acceptance_requires_full_recomputation") is not True:
        raise Iteration8EpisodeValidationError("Iteration 8 semantic repair acceptance requires recomputation")
    memory = contract.get("memory_contract", {})
    if memory.get("free_text_distinction_signature_allowed") is not False:
        raise Iteration8EpisodeValidationError("Iteration 8 distinction_signature cannot be free text")
    if tuple(memory.get("enumerated_distinction_signature_values", ())) != ALLOWED_ENUMERATED_DISTINCTION_SIGNATURE_VALUES:
        raise Iteration8EpisodeValidationError("Iteration 8 distinction_signature enum allowlist mismatch")
    if tuple(memory.get("structured_distinction_signature_values", ())) != ALLOWED_STRUCTURED_DISTINCTION_SIGNATURE_VALUES:
        raise Iteration8EpisodeValidationError("Iteration 8 distinction_signature structured allowlist mismatch")
    return {"status": "pass", "action_count": len(ITERATION8_LEARNER_ACTIONS)}


def validate_learner_visible_memory(memory: dict[str, Any]) -> dict[str, Any]:
    findings = scan_iteration8_model_visible_payload(memory)
    if findings:
        raise Iteration8EpisodeValidationError(f"learner-visible memory leakage: {findings[0]}")
    if memory.get("memory_type") != "quotient_repair_module":
        raise Iteration8EpisodeValidationError("learner-visible memory type mismatch")
    scope = memory.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"domain_family", "consumer_family", "operator_family"}:
        raise Iteration8EpisodeValidationError("learner-visible memory scope mismatch")
    if memory.get("repair_operator") not in MEMORY_REPAIR_OPERATORS:
        raise Iteration8EpisodeValidationError("learner-visible memory repair operator mismatch")
    _validate_distinction_signature(memory.get("distinction_signature"))
    return {"status": "pass"}


def validate_iteration8_evidence_timeline(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    if not timeline:
        raise Iteration8EpisodeValidationError("empty evidence timeline")
    first_observation = timeline[0].get("model_visible_observation", {})
    if _observation_reveals_anti_witness(first_observation):
        raise Iteration8EpisodeValidationError("preloaded anti-witness evidence at reset")

    for event in timeline:
        action = event.get("action")
        observation = event.get("model_visible_observation", {})
        if _observation_reveals_anti_witness(observation) and action not in {"request_anti_witness", "point_anti_witness"}:
            raise Iteration8EpisodeValidationError("anti-witness reveal requires request_anti_witness action")
    return {"status": "pass", "event_count": len(timeline)}


def _validate_distinction_signature(signature: Any) -> None:
    if not isinstance(signature, dict):
        raise Iteration8EpisodeValidationError("distinction_signature must be structured, not free text")
    if signature.get("kind") not in DISTINCTION_SIGNATURE_KINDS:
        raise Iteration8EpisodeValidationError("distinction_signature kind is not allowed")
    value = signature.get("value")
    if not isinstance(value, str) or not value:
        raise Iteration8EpisodeValidationError("distinction_signature value missing")
    if signature.get("kind") == "enumerated_operator_family" and value not in ALLOWED_ENUMERATED_DISTINCTION_SIGNATURE_VALUES:
        raise Iteration8EpisodeValidationError("distinction_signature enumerated value is not allowed")
    if signature.get("kind") == "structured_non_label_descriptor" and value not in ALLOWED_STRUCTURED_DISTINCTION_SIGNATURE_VALUES:
        raise Iteration8EpisodeValidationError("distinction_signature structured value is not allowed")
    lowered = value.lower()
    for token in DISTINCTION_SIGNATURE_FORBIDDEN_VALUE_TOKENS:
        if token in lowered:
            raise Iteration8EpisodeValidationError(f"distinction_signature leaks recoverable token {token}")
    if _looks_like_long_hash(value):
        raise Iteration8EpisodeValidationError("distinction_signature leaks hash-like value")


def _key_matches_denied(key_text: str, denied: str) -> bool:
    if key_text == denied:
        return True
    # Allow benign stable handles and root field names; deny explicit target/evidence keys.
    if denied in {"hash", "split", "label", "success", "status"}:
        return key_text in {denied, f"{denied}_name", f"{denied}_flag", f"{denied}_token"} or key_text.endswith(f"_{denied}")
    return denied in key_text


def _looks_like_long_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{32,}", value))


def _observation_reveals_anti_witness(observation: Any) -> bool:
    if isinstance(observation, dict):
        if observation.get("kind") == "anti_witness_revealed":
            return True
        return any(_observation_reveals_anti_witness(child) or "anti_witness" in str(key).lower() for key, child in observation.items())
    if isinstance(observation, (list, tuple)):
        return any(_observation_reveals_anti_witness(item) for item in observation)
    if isinstance(observation, str):
        return "anti_witness" in observation.lower()
    return False
