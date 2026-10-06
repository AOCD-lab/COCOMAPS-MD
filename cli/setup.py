from pathlib import Path

from setuptools import find_namespace_packages, setup


ROOT = Path(__file__).parent
SUBPACKAGES = [f'cli.{name}' for name in find_namespace_packages(where=str(ROOT))]

setup(
    name='cocomaps-md-cli',
    version='1.1.0',
    description='Self-contained COCOMAPS-MD command-line analysis and charting tool',
    packages=['cli', *SUBPACKAGES],
    package_dir={'cli': '.'},
    include_package_data=True,
    package_data={
        'cli._runtime': [
            'deps/*/*',
            'stubs/*/*',
            'stubs/*/*/*',
            'cocomaps/*.json',
            'cocomaps/*.md',
            'cocomaps/*.txt',
            'engine/*.md',
            '*.js',
        ],
    },
    python_requires='>=3.10',
    install_requires=[
        'MDAnalysis>=2.6',
        'pandas==2.2.2',
        'networkx',
        'biopython>=1.83',
        'scipy>=1.14.0',
        'bidict>=0.23',
        'python-dotenv',
        'rich>=13.0',
        'plotly>=5.0,<7',
        'kaleido==0.2.1',
    ],
    entry_points={'console_scripts': ['coco-md=cli.main:main']},
)
