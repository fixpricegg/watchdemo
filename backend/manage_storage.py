"""Run explicitly against the intended database: python manage_storage.py migrate."""
import argparse
import os

from storage.repository import Repository


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "check"])
    args = parser.parse_args()
    repository = Repository(os.environ.get("WATCHDEMO_DATABASE_URL"))
    if args.command == "migrate":
        repository.migrate()
    repository.check_schema()
    print("WatchDemo storage schema is up to date")
