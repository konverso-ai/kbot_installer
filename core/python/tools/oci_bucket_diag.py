#!/usr/bin/env python3
"""Standalone OCI Object Storage diagnostic script (no kbot code involved).

Usage:
    python oci_bucket_diag.py \
        --bucket-name konverso-oci-kbot-master-bucket \
        --auth instance_principal \
        [--namespace <namespace>] \
        [--region eu-paris-1] \
        [--compartment-id ocid1.compartment.oc1..xxx]

If --namespace is omitted, it is resolved via get_namespace().
If --compartment-id is omitted, bucket creation is skipped (it is required by the API).
"""
import argparse
import sys

import oci
import oci.object_storage
from oci.exceptions import ServiceError


def get_signer(auth_method: str):
    if auth_method == "instance_principal":
        return oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    if auth_method == "resource_principal":
        return oci.auth.signers.get_resource_principals_signer()
    raise ValueError(f"Unsupported auth_method: {auth_method}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--auth", default="instance_principal", choices=["instance_principal", "resource_principal"])
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--region", default=None)
    parser.add_argument("--compartment-id", default=None, help="Required only to attempt bucket creation.")
    args = parser.parse_args()

    print(f"[1] Building signer (auth_method={args.auth}) ...")
    signer = get_signer(args.auth)
    print(f"    signer region: {getattr(signer, 'region', None)}")

    config = {}
    if args.region:
        config["region"] = args.region
        print(f"    forcing region: {args.region}")

    print("[2] Creating ObjectStorageClient ...")
    client = oci.object_storage.ObjectStorageClient(config=config, signer=signer)
    print(f"    client region in use: {client.base_client.config.get('region')}")

    namespace = args.namespace
    if not namespace:
        print("[3] Resolving namespace via get_namespace() ...")
        namespace = client.get_namespace().data
    print(f"    namespace: {namespace}")

    # Note: get_bucket() requires the "inspect/manage buckets" IAM permission, distinct from
    # "manage objects". A dynamic-group policy scoped to objects only will make get_bucket
    # return a 404 even though the bucket exists and list_objects/put_object work fine.
    print(f"[4] LIST objects (bucket existence check) '{args.bucket_name}' ...")
    try:
        client.list_objects(namespace, args.bucket_name, limit=1)
        bucket = True
        print("    OK - bucket is accessible.")
    except ServiceError as e:
        print(f"    FAILED - status={e.status} code={e.code} message={e.message}")
        bucket = None

    if bucket is None and args.compartment_id:
        print(f"[5] Bucket not found - attempting CREATE in compartment {args.compartment_id} ...")
        try:
            details = oci.object_storage.models.CreateBucketDetails(
                name=args.bucket_name,
                compartment_id=args.compartment_id,
            )
            created = client.create_bucket(namespace, details).data
            print(f"    OK - bucket created. compartment_id={created.compartment_id}")
        except ServiceError as e:
            print(f"    FAILED - status={e.status} code={e.code} message={e.message}")
            return 1
    elif bucket is None:
        print("[5] Skipping create (no --compartment-id provided).")
        return 1

    print(f"[6] LIST objects in bucket '{args.bucket_name}' ...")
    try:
        response = client.list_objects(namespace, args.bucket_name)
        names = [obj.name for obj in (response.data.objects or [])]
        print(f"    OK - {len(names)} object(s): {names[:20]}")
    except ServiceError as e:
        print(f"    FAILED - status={e.status} code={e.code} message={e.message}")
        return 1

    test_key = "oci_bucket_diag_test.txt"
    print(f"[7] PUT object '{test_key}' ...")
    try:
        client.put_object(namespace, args.bucket_name, test_key, b"oci_bucket_diag test file\n")
        print("    OK - object uploaded.")
    except ServiceError as e:
        print(f"    FAILED - status={e.status} code={e.code} message={e.message}")
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
