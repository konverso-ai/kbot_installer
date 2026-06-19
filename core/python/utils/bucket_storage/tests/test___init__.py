"""Tests for utils.bucket_storage.__init__ (BucketStorage ABC)."""
from abc import ABC

import pytest

from utils.bucket_storage import BucketStorage


ABSTRACT_METHODS = [
    "get",
    "set",
    "delete",
    "list",
    "list_files_in_folder",
    "delete_folder",
    "restore_soft_deleted_blob",
    "list_folders",
]


@pytest.mark.parametrize("method_name", ABSTRACT_METHODS)
def test_bucket_storage_declares_abstract_method(method_name):
    assert getattr(BucketStorage, method_name).__isabstractmethod__


@pytest.mark.parametrize("method_name", ABSTRACT_METHODS)
def test_incomplete_subclass_cannot_be_instantiated(method_name):
    implemented = {m: (lambda self, *a, **k: None) for m in ABSTRACT_METHODS if m != method_name}

    IncompleteStorage = type(
        "IncompleteStorage",
        (BucketStorage,),
        {**implemented, "name": "incomplete"},
    )

    with pytest.raises(TypeError):
        IncompleteStorage()


def test_complete_subclass_can_be_instantiated():
    class CompleteStorage(BucketStorage):
        name = "complete"

        def get(self, key, encoding="utf-8"):
            return None

        def set(self, key, value, encoding="utf-8"):
            return None

        def delete(self, key):
            return None

        def list(self, prefix=""):
            return []

        def list_files_in_folder(self, folder_path=""):
            return []

        def delete_folder(self, key):
            return None

        def restore_soft_deleted_blob(self, key):
            return False

        def list_folders(self, path=""):
            return []

    instance = CompleteStorage()
    assert isinstance(instance, BucketStorage)
    assert isinstance(instance, ABC)
