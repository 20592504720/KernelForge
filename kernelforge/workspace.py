"""Portable workspace paths; machine-specific locations stay outside Git."""
from __future__ import annotations

import json
import os
from pathlib import Path

KINDS = ('project','sources','toolchains','cache','builds','artifacts','logs','reports','temp','manifests','backups')


class Workspace:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()

    @classmethod
    def configured(cls):
        home = os.environ.get('KERNELFORGE_HOME')
        return cls(home) if home else None

    def path(self, kind, *parts):
        if kind not in KINDS:
            raise ValueError(f'unknown workspace category: {kind}')
        base = self.home.joinpath(kind).resolve()
        path = base.joinpath(*parts).resolve()
        if self.home not in base.parents or (path != base and base not in path.parents):
            raise ValueError('workspace path escapes KERNELFORGE_HOME')
        return path

    def manifest(self):
        return {'schema_version':1,'home':str(self.home),
                'paths':{kind:str(self.path(kind)) for kind in KINDS},
                'linux_kernel_build_status':'UNTESTED',
                'note':'Windows/NTFS development paths are not a verified Linux kernel build filesystem'}

    def temporary_environment(self):
        folder=self.path('temp')
        folder.mkdir(parents=True,exist_ok=True)
        return {key:str(folder) for key in ('TEMP','TMP','TMPDIR')}

    def initialize(self):
        for kind in KINDS:
            self.path(kind).mkdir(parents=True,exist_ok=True)
        destination=self.path('manifests','workspace.json')
        if destination.exists():
            existing=json.loads(destination.read_text(encoding='utf-8'))
            if existing.get('home') != str(self.home):
                raise ValueError('existing workspace manifest belongs to another location')
        destination.write_text(json.dumps(self.manifest(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return destination


def default_path(kind, fallback, *parts):
    configured=Workspace.configured()
    return configured.path(kind,*parts) if configured else Path(fallback)
