from bmaster.maintenance import main as maintenance_main
from bmaster.maintenance import run_update


def main() -> int:
    return maintenance_main(["update"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Update failed: {exc}")
        raise SystemExit(1)
