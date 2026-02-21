import argparse
from bmaster.maintenance import bootstrap

def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"--update-cert",
		action="store_true",
		help="Force regenerate SSL certificate even if it already exists",
	)
	args, _ = parser.parse_known_args()
	return bootstrap(update_cert=args.update_cert)


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Setup failed: {exc}")
		raise SystemExit(1)
