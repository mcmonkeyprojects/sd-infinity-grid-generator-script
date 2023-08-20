import launch

if not launch.is_installed("yaml"):
    launch.run_pip("install pyyaml", "pyyaml for Infinity Grid Script")
if not launch.is_installed("pyyaml-include"):
    launch.run_pip("install pyyaml-include", "pyyaml-include for Infinity Grid Script")
