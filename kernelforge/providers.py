"""Layout policies for current upstreams; mutation remains in the shared engine."""
import re


class OfficialModern:
    name = 'Official-Kbuild-v2'

    def validate(self, kernel):
        for relative in ('Kbuild', 'Makefile', 'Kconfig', 'core/init.c', 'hook/setuid_hook.c'):
            if not (kernel / relative).is_file():
                raise ValueError(f'official modern source layout changed: missing {relative}')
        build = (kernel / 'Kbuild').read_text(encoding='utf-8')
        wrapper = (kernel / 'Makefile').read_text(encoding='utf-8')
        if 'obj-$(CONFIG_KSU)' not in build or 'core/init.o' not in build or 'KBUILD_ARGS' not in wrapper:
            raise ValueError('official modern Kbuild/module wrapper layout is unsupported')
        kconfig = (kernel / 'Kconfig').read_text(encoding='utf-8')
        if not re.search(r'^config KSU$', kconfig, re.MULTILINE):
            raise ValueError('official modern KSU Kconfig missing')
        return {'adapter': self.name, 'build_file': 'kernel/Kbuild',
                'module_wrapper': 'kernel/Makefile', 'upstream_recommended_mode': 'LKM',
                'integration_mode': 'experimental builtin Kbuild', 'compile_status': 'UNTESTED'}


class BakaModern:
    name = 'BakaSU-Kbuild-v2'

    def validate(self, kernel):
        for relative in ('Kbuild', 'core/init.c', 'tools/susfs_compat.mk'):
            if not (kernel / relative).is_file():
                raise ValueError(f'BakaSU current layout changed: missing {relative}')
        build = (kernel / 'Kbuild').read_text(encoding='utf-8')
        if 'obj-$(CONFIG_KSU)' not in build or 'core/init.o' not in build or 'CONFIG_KSU_TRACEPOINT_HOOK' not in build:
            raise ValueError('BakaSU hook/Kbuild layout changed; adapter review required')
        return {'adapter': self.name, 'build_file': 'kernel/Kbuild', 'compile_status': 'UNTESTED'}
