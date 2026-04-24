from .base import Plugin

class SummarizeFilePlugin(Plugin):
    name = "summarize_file"
    capabilities = ["summarize_file"]

    def run(self, ctx, inputs):
        return {"status": "stub"}
