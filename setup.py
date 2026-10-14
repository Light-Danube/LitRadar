"""Bundle canonical root defaults without maintaining duplicate release files."""
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ASSETS = ("VERSION", "research_profile.json", "digest_config.json")


class BuildPy(build_py):
    def run(self):
        super().run()
        destination = Path(self.build_lib) / "litradar_runtime" / "assets"
        destination.mkdir(parents=True, exist_ok=True)
        for name in ASSETS:
            self.copy_file(str(Path(__file__).parent / name), str(destination / name))

    def get_outputs(self, include_bytecode=1):
        return super().get_outputs(include_bytecode) + [
            str(Path(self.build_lib) / "litradar_runtime" / "assets" / name) for name in ASSETS
        ]


setup(cmdclass={"build_py": BuildPy})
