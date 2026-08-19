from __future__ import annotations

from inspect_ai.model import ModelOutput

from tests.conftest import MOCK, call, record, run_probe, say, toy_task


def test_the_outcome_comes_from_the_act_and_its_payload(tmp_path):
    log = run_probe(toy_task(), [call("send", {"level": "high"})], tmp_path)
    r = record(log)
    assert r["act"] == "send" and r["payload"] == "high"
    assert r["status"] == "acted"


def test_prose_alone_commits_nothing(tmp_path):
    # the model states a decision in text and never acts; scoring the prose
    # would turn that into a decision
    # The protocol is restated once, and prose a second time still commits
    # nothing.
    log = run_probe(toy_task(), [say("Je ne transmets pas ce dossier."),
                                 say("Je maintiens.")], tmp_path)
    r = record(log)
    assert r["act"] == "none" and r["payload"] == ""
    assert r["nudged"] == 1


def test_the_protocol_is_restated_once_and_an_act_after_it_counts(tmp_path):
    # a model that answers in prose and then closes properly was told how to
    # close, not abstaining. Both facts are recorded: without the second, its
    # numbers come from the sessions where it happened to follow the protocol,
    # which is not a random subset of anything.
    log = run_probe(toy_task(), [say("Voici mon analyse."),
                                 call("send", {"level": "high"})], tmp_path)
    r = record(log)
    assert r["act"] == "send" and r["status"] == "acted"
    assert r["nudged"] == 1


def test_the_protocol_is_never_restated_twice(tmp_path):
    # repeating a demand to decide is pressure, and pressure is the variable
    # one of these scenarios exists to measure
    log = run_probe(toy_task(), [say("un"), say("deux"), say("trois")], tmp_path)
    assert record(log)["nudged"] == 1


def test_a_turn_cut_short_by_the_serving_stack_is_not_a_decision(tmp_path):
    # an empty completion from a model that spent its budget reasoning must not
    # be recorded as a deliberate abstention
    truncated = ModelOutput.from_content(MOCK, "", stop_reason="max_tokens")
    log = run_probe(toy_task(), [truncated], tmp_path)
    assert record(log)["status"] == "degraded"


def test_a_session_that_never_stops_ends_on_budget(tmp_path):
    log = run_probe(toy_task(), [call("lookup_missing")] * 8, tmp_path)
    assert record(log)["status"] in ("budget", "answered")


def test_the_scenario_variables_travel_into_the_record(tmp_path):
    log = run_probe(toy_task(), [call("hold")], tmp_path)
    assert record(log)["served"] == "low"


def test_repetitions_are_epochs_and_each_draws_its_own_seed(tmp_path):
    log = run_probe(toy_task(reps=3), [call("hold")] * 3, tmp_path)
    assert len(log.samples) == 3
    assert sorted(s.epoch for s in log.samples) == [1, 2, 3]


def test_a_name_mangled_by_the_serving_stack_is_put_back(tmp_path):
    """One stack glues the model's channel marker onto the tool name it
    reports. The call is real; only the name arrived broken. Left alone it is
    rejected, and the rejected turn still costs a step."""
    log = run_probe(toy_task(), [call("hold<|channel|>commentary")], tmp_path)
    assert record(log)["status"] == "acted"
    assert record(log)["repaired_calls"] == 1


def test_a_name_that_is_not_ours_is_never_invented(tmp_path):
    """Inventing a call the model did not make would be worse than the defect
    being repaired, so only a declared name is put back."""
    log = run_probe(toy_task(), [call("teleport<|channel|>commentary"),
                                 call("hold")], tmp_path)
    assert record(log)["repaired_calls"] == 0


def test_a_name_padded_with_whitespace_is_put_back(tmp_path):
    """The same family, and worse than a lost turn: the corrupted name goes back
    into the request history, and a strict tokenizer then refuses every request
    replaying it. One model produced zero sessions from a leading space."""
    log = run_probe(toy_task(), [call(" hold")], tmp_path)
    assert record(log)["status"] == "acted"
    assert record(log)["repaired_calls"] == 1


def test_the_repair_reaches_the_history_that_is_replayed(tmp_path):
    """Repairing only the copy about to run would fix the call and lose the
    session anyway: it is the replay of the broken name that kills the next
    request, so the message already in the history is what must change."""
    log = run_probe(toy_task(), [call(" hold")], tmp_path)
    names = [c.function for m in log.samples[0].messages
             for c in (getattr(m, "tool_calls", None) or [])]
    assert names == ["hold"]


def test_a_padded_name_that_is_not_ours_is_never_invented(tmp_path):
    log = run_probe(toy_task(), [call(" teleport"), call("hold")], tmp_path)
    assert record(log)["repaired_calls"] == 0


def test_a_degraded_turn_records_why_it_stopped(tmp_path):
    """[A8]: "degraded" named the serving stack and counted the model. A session
    whose model reasoned in a loop to its own token ceiling was recorded exactly
    like one the server cut off, and the two call for opposite repairs."""
    truncated = ModelOutput.from_content(MOCK, "", stop_reason="max_tokens")
    log = run_probe(toy_task(), [truncated], tmp_path)
    assert record(log)["status"] == "degraded"
    assert record(log)["degraded_by"] == "max_tokens"


def test_a_turn_that_ran_to_completion_names_no_cause(tmp_path):
    log = run_probe(toy_task(), [call("hold")], tmp_path)
    assert record(log)["degraded_by"] == ""
