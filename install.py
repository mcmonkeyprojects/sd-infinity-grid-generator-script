import launch

if not launch.is_installed("pyyaml"):
    launch.run_pip("install pyyaml", "pyyaml for Infinity Grid Script")
