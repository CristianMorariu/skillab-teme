import yaml
from jinja2 import Template
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    # Reprezentarea internă a unui fișier YAML de prompt
    name: str
    version: str
    prompt: str
    description: str = ""


class PromptRegistry:
    def __init__(self, folder: str):
        self._templates = self._load(folder)

    def _load(self, folder: str) -> dict[str, PromptTemplate]:
        # Citește toate .yaml din folder → dict {name: PromptTemplate}
        templates = {}
        for path in Path(folder).rglob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            tpl = PromptTemplate(**data)
            templates[tpl.name] = tpl
        return templates

    def render(self, name: str, **variabile) -> str:
        template = self._templates[name]
        return Template(template.prompt).render(**variabile)
