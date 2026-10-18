"""Session-local evidence projection. Edges describe provenance, never identity proof."""
import networkx as nx


def evidence_graph(conversation):
    graph = nx.DiGraph()
    for sid, segment in conversation.segments.items():
        source = f"segment:{sid}:{segment.revision}"
        graph.add_node(source, type="segment", segment_id=sid,
                       revision=segment.revision, final=segment.final,
                       role=segment.role, start_ms=segment.start_ms,
                       end_ms=segment.end_ms, provider_speaker=segment.provider_speaker)
        for index, event in enumerate(conversation.events.get(sid, [])):
            # Namespace and ordinal prevent custom extractor IDs merging nodes.
            node = f"event:{sid}:{segment.revision}:{index}"
            graph.add_node(node, type="risk_event", event_id=event.event_id,
                           kind=event.kind, start=event.start, end=event.end,
                           extractor=event.extractor, provisional=not segment.final)
            graph.add_edge(source, node, relation="extracted_from_segment")
            if segment.final:
                category = f"risk:{event.kind}"
                graph.add_node(category, type="risk_category", kind=event.kind)
                graph.add_edge(node, category, relation="supports_current_risk")
    # Return detached plain data; clients cannot mutate the engine through this view.
    return {
        "schema_version": "evidence-graph-v1",
        "scope": "current_session_revisions",
        "nodes": [dict(id=node, **data) for node, data in graph.nodes(data=True)],
        "edges": [dict(source=u, target=v, **data) for u, v, data in graph.edges(data=True)],
        "policy_state": conversation.state,
        "policy_note": ("All live restrictions may remain latched after correction; graph shows current evidence only."
                        if hasattr(conversation, 'safety_categories') else
                        "BLOCKED and COOLING_OFF may remain latched after evidence correction; graph shows current evidence only."),
        "retained_safety_categories": sorted(getattr(conversation, 'safety_categories', set())),
        "identity_verified": False,
        "protected_actions_allowed": False,
    }
