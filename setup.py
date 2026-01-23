from setuptools import setup
try:
    from wheel.bdist_wheel import bdist_wheel
    class bdist_wheel_abi3(bdist_wheel):
        def finalize_options(self):
            super().finalize_options()
            self.root_is_pure = False
            self.python_tag = "py3"
except ImportError:
    bdist_wheel_abi3 = None

setup(
    cmdclass={"bdist_wheel": bdist_wheel_abi3} if bdist_wheel_abi3 else {},
)
