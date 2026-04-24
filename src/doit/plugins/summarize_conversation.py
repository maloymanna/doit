from .base import Plugin

class SummarizeConversationPlugin(Plugin):
    name = "summarize_conversation"
    capabilities = ["summarize_conversation"]

    def run(self, ctx, inputs):
        return {"status": "stub"}
