def test_failure_and_utility_rehearsal():
    from scripts.proof_demo import rehearsal
    result = rehearsal()
    assert result['counterfactual']['http_status'] == 403
    assert result['valid_simulated_approval'] == 'simulated_action_completed'
    assert result['real_action_executed'] is False
