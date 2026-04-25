from typing import Callable, Optional


class PermissionError(Exception):
    pass


class Permissions:
    """
    Simple permissions helper.

    - `prompt_user_fn` is optional for non-interactive runs.
    - If not provided, a default non-interactive prompt is used that raises
      PermissionError for any interactive confirmation request.
    """

    def __init__(self, workspace_root: str, prompt_user_fn: Optional[Callable[[str], bool]] = None):
        self.workspace_root = workspace_root
        # default prompt function: non-interactive (safe)
        if prompt_user_fn is None:
            def _default_prompt(msg: str) -> bool:
                # Non-interactive default: deny interactive requests.
                raise PermissionError(f"Interactive prompt required but no prompt_user_fn provided: {msg}")
            self.prompt_user_fn = _default_prompt
        else:
            self.prompt_user_fn = prompt_user_fn

    def confirm(self, message: str) -> bool:
        """
        Ask user for confirmation. If no interactive prompt is available,
        this will raise PermissionError.
        """
        return bool(self.prompt_user_fn(message))

    # convenience factory used by other modules
    @classmethod
    def non_interactive(cls, workspace_root: str):
        return cls(workspace_root, prompt_user_fn=None)
