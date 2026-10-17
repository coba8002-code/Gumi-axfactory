"""Operator CLI: credential input is environment-only; never printed."""
import argparse
import hashlib
import os
from uuid import UUID, uuid4
from .db import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", type=UUID, required=True)
    parser.add_argument("--factory", type=UUID, required=True)
    parser.add_argument("--role", choices=["admin", "supervisor", "worker", "device"], required=True)
    args = parser.parse_args()
    token = os.environ["PROVISION_TOKEN"]
    if len(token) < 32:
        raise SystemExit("PROVISION_TOKEN requires at least 32 random characters")
    with connect() as db:
        identity = uuid4()
        db.execute("INSERT INTO identities(id,tenant_id,factory_id,role,token_hash) VALUES (%s,%s,%s,%s,%s)",
                   (identity, args.tenant, args.factory, args.role, hashlib.sha256(token.encode()).hexdigest()))
    print(identity)


if __name__ == "__main__":
    main()
