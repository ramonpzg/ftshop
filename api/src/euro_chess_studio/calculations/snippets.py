"""Valid mini-IDE snippet ids. Snippet content itself lives in the frontend
(web/src/lib/snippets.ts) since it's a display concern; the backend only
needs to know which ids are valid so it can persist a workspace's selection.
"""

VALID_SNIPPET_IDS = frozenset(
    {
        "prompt_template",
        "legal_move_validation",
        "dataset_row_builder",
        "reward_function",
        "chat_template",
        "fine_tune",
    }
)
