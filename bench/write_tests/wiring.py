"""Wire lib/agent_kunit.c into the kernel build: Makefile rule, Kconfig symbol,
empty placeholder file. Applied to a worktree before the agent runs and again
before grading, so the agent never has to touch the build system."""
from pathlib import Path

KCONFIG = '''
config AGENT_KUNIT_TEST
	tristate "KUnit test written by an agent" if !KUNIT_ALL_TESTS
	depends on KUNIT
	default KUNIT_ALL_TESTS
'''
PLACEHOLDER = '''// SPDX-License-Identifier: GPL-2.0
/*
 * lib/agent_kunit.c: KUnit test written by an agent for this benchmark.
 * This file is compiled when CONFIG_AGENT_KUNIT_TEST is set.
 */
'''


def apply(wt):
    wt = Path(wt)
    mk = wt / 'lib/Makefile'
    text = mk.read_text()
    if 'CONFIG_AGENT_KUNIT_TEST' not in text:
        text = text.replace('obj-$(CONFIG_STRING_KUNIT_TEST) += string_kunit.o\n',
                            'obj-$(CONFIG_STRING_KUNIT_TEST) += string_kunit.o\n'
                            'obj-$(CONFIG_AGENT_KUNIT_TEST) += agent_kunit.o\n')
        assert 'CONFIG_AGENT_KUNIT_TEST' in text, 'Makefile anchor not found'
        mk.write_text(text)
    kc = wt / 'lib/Kconfig.debug'
    text = kc.read_text()
    if 'AGENT_KUNIT_TEST' not in text:
        anchor = 'config STRING_KUNIT_TEST\n'
        assert anchor in text, 'Kconfig anchor not found'
        text = text.replace(anchor, KCONFIG.lstrip('\n') + '\n' + anchor)
        kc.write_text(text)
    (wt / 'lib/agent_kunit.c').write_text(PLACEHOLDER)
