class TaskContext:
    def __init__(self, project_name, config, files, browser, git, logger):
        self.project_name = project_name
        self.config = config
        self.files = files
        self.browser = browser
        self.git = git
        self.logger = logger

class Plugin:
    name: str = ""
    capabilities: list[str] = []

    def run(self, task_context: TaskContext, inputs: dict) -> dict:
        raise NotImplementedError
