"""Shared fixtures and import stubs for bucket_storage tests."""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _install_module(name, attrs=None):
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    if attrs:
        for key, value in attrs.items():
            setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_import_stubs():
    """Stub heavy optional dependencies before importing kbot modules."""
    _install_module("bs4", {"BeautifulSoup": MagicMock()})
    _install_module("magic")
    _install_module("django")
    _install_module("django.conf", {"settings": MagicMock()})
    _install_module("django.utils", {"timezone": MagicMock()})
    _install_module("Crypto")
    _install_module("Crypto.Random")
    _install_module("Crypto.Cipher")
    _install_module("Crypto.Cipher.AES")
    _install_module("cryptography")
    _install_module("cryptography.hazmat")
    cryptography_primitives = _install_module("cryptography.hazmat.primitives")
    cryptography_primitives.padding = MagicMock()
    _install_module(
        "cryptography.hazmat.primitives.ciphers",
        {"Cipher": MagicMock(), "algorithms": MagicMock(), "modes": MagicMock()},
    )
    _install_module("cryptography.hazmat.backends", {"default_backend": MagicMock()})
    _install_module("common")
    _install_module("common.Errors", {"StopThread": Exception, "QuestionSkipped": Exception, "SurveySkipped": Exception})
    _install_module("pythonjsonlogger")
    _install_module("pythonjsonlogger.json", {"JsonFormatter": MagicMock()})
    _install_module("errors", {"ErrorCode": MagicMock()})
    _install_module("psutil")
    _install_module("security")
    _install_module("classification", {"ClassifierFactory": MagicMock()})
    _install_module("communication", {"MessageBroker": MagicMock()})
    _install_module("ticket")
    _install_module("dialog", {"intention": types.ModuleType("dialog.intention")})
    _install_module("dialog.intention", {"IntentionFactory": MagicMock()})

    bot_module = _install_module("Bot")
    bot_module.Bot = MagicMock()

    _install_module("boto3", {"client": MagicMock()})
    botocore_exceptions = _install_module("botocore.exceptions")

    class _ClientError(Exception):
        def __init__(self, response, operation_name=None):
            super().__init__(operation_name or "ClientError")
            self.response = response

    botocore_exceptions.ClientError = _ClientError
    botocore_exceptions.NoCredentialsError = type("NoCredentialsError", (Exception,), {})

    azure_core = _install_module("azure.core")
    azure_core_exceptions = _install_module("azure.core.exceptions")
    azure_core_exceptions.ResourceNotFoundError = type("ResourceNotFoundError", (Exception,), {})
    azure_core_exceptions.ClientAuthenticationError = type("ClientAuthenticationError", (Exception,), {})
    azure_core_exceptions.ResourceExistsError = type("ResourceExistsError", (Exception,), {})

    _install_module("azure.identity", {"DefaultAzureCredential": MagicMock()})

    class _BlobPrefix:
        def __init__(self, prefix):
            self.prefix = prefix

    _install_module(
        "azure.storage.blob",
        {"BlobServiceClient": MagicMock(), "BlobPrefix": _BlobPrefix},
    )


_install_import_stubs()


@pytest.fixture
def mock_bot_config():
    """Provide a configurable Bot.GetConfig mock."""
    config = {
        "aws_s3_region": "us-east-1",
        "aws_s3_bucket_name": "test-bucket",
        "cluster_name": "test-cluster",
        "kbot_storage_account": "https://testaccount.blob.core.windows.net",
        "storage_account_container_name": "test-container",
    }

    def get_config(key, default=None):
        return config.get(key, default)

    with patch("Bot.Bot") as mock_bot_cls:
        mock_bot_cls.return_value.GetConfig.side_effect = get_config
        yield config, mock_bot_cls


@pytest.fixture
def reset_factory_singleton():
    """Reset Factory singleton between tests."""
    from utils.bucket_storage.factory import Factory

    Factory._instances.pop(Factory, None)
    yield
    Factory._instances.pop(Factory, None)
