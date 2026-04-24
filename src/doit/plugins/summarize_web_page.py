from .base import Plugin

class SummarizeWebPagePlugin(Plugin):
    name = "summarize_web_page"
    capabilities = ["summarize_web_page"]

    def run(self, ctx, inputs):
        return {"status": "stub"}
