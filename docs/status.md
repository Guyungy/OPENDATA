# Status

## Current milestone

**Milestone focus:** P1-2 Taxonomy / Ontology Builder.

Implemented in this update:
- Added canonical taxonomy artifact `canonical/taxonomy.json` with explicit TaxonomyNode contracts (`id`, `name`, `node_type`, `parent_id`, `source_refs`, `confidence`, `status`, `created_at`, `updated_at`).
- Added canonical ontology artifact `canonical/ontology.json` with type-level OntologyEntry patterns (`subject_type`, `relation_type`, `object_type`) derived from canonical relation evidence.
- Added governance artifact `governance/taxonomy_candidates.json` for uncertain taxonomy/ontology proposals before promotion.
- Added lightweight taxonomy/ontology builder stage to the pipeline, using canonical entities/relations/claims and schema signals to:
  - promote stable structures,
  - route uncertain additions to taxonomy candidates,
  - emit `taxonomy_promotion` review items instead of silent promotion.
- Extended review decision handling to consume `taxonomy_promotion` items, updating canonical taxonomy/ontology only on accepted decisions and tracking rejected/deferred outcomes.
- Added dashboard taxonomy/ontology sections and changelog metrics (`taxonomy_nodes_added`, `ontology_patterns_added`, `taxonomy_candidates_created`, `taxonomy_candidates_promoted`, `taxonomy_candidates_rejected`).
- Regenerated sample workspace artifacts with taxonomy/ontology outputs and taxonomy candidate governance state.

## Validation status

- `PYTHONPATH=src pytest -q` passes, including new behavior tests for:
  - taxonomy node generation from canonical knowledge,
  - uncertain taxonomy additions routed to taxonomy candidates,
  - accepted taxonomy review promotion path,
  - ontology artifact generation from relation patterns,
  - dashboard taxonomy/ontology metrics rendering.
- Sample pipeline run completed on `workspaces/sample` with updated canonical/governance artifacts.

## Next tasks

1. Add stronger taxonomy parenting heuristics for category/tag hierarchy while preserving conservative governance defaults.
2. Add drift/consistency checks between canonical schema types and active taxonomy entity_type nodes.
3. Add snapshot-level trend summaries for taxonomy candidate closure velocity.
