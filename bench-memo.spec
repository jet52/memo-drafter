# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / 'src' / 'cli.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'config' / 'prompts'), 'config/prompts'),
        (str(ROOT / 'config' / 'settings.py'), 'config'),
        (str(ROOT / 'config' / 'style_specification.py'), 'config'),
        (str(ROOT / 'config' / '__init__.py'), 'config'),
        (str(ROOT / 'config' / 'prompts' / '__init__.py'), 'config/prompts'),
    ],
    hiddenimports=[
        'anthropic',
        'pdfminer',
        'pdfminer.high_level',
        'pdfminer.layout',
        'click',
        'httpx',
        'dotenv',
        'diskcache',
        'rich',
        'pydantic',
        'pydantic_settings',
        'src',
        'src.cli',
        'src.generator',
        'src.generator.claude_client',
        'src.generator.memo_generator',
        'src.extractor',
        'src.classifier',
        'src.verifier',
        'src.output',
        'src.utils',
        'src.utils.logging',
        'config',
        'config.settings',
        'config.style_specification',
        'config.prompts',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'pytest_asyncio',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='bench-memo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
