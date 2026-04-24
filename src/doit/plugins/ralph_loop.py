from .base import Plugin

class RalphLoopPlugin(Plugin):
    name = "ralph_loop"
    capabilities = ["ralph_loop"]

    def run(self, ctx, inputs):
        return {"status": "stub"}
