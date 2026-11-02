#!/usr/bin/env python3
from common.entrypoint import run_arm_recipe_with_model_forge


if __name__ == "__main__":
    raise SystemExit(
        run_arm_recipe_with_model_forge(
            "excavator", "MathScavator9000 Excavator"
        )
    )
