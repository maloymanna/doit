from .base import Plugin

class SummarizeYouTubePlugin(Plugin):
    name = "summarize_youtube"
    capabilities = ["summarize_youtube"]

    def run(self, ctx, inputs):
        return {"status": "stub"}
