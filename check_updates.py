from bmaster.maintenance import main as maintenance_main
from bmaster.maintenance import run_check


def main() -> int:
    return maintenance_main(["check"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Check failed: {exc}")
        raise SystemExit(1)
