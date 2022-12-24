import os
from hypothesis import settings, Verbosity

settings.register_profile("smoke", max_examples=5)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
