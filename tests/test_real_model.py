"""Offline-safety and owner-rules tests for the real-model client.

These tests never touch the network: they verify the module is inert
without a key, rejects non-pinned models, and maps billing errors to the
owner-mandated STOP exception.
"""

import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from agency_bench import real_model
from agency_bench.real_model import (
    DEFAULT_BASE_URL,
    PINNED_MODEL,
    BillingError,
    RealModelNotConfigured,
    chat,
    resolve_config,
)


def _clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("AGENCY_ZAI_")}
    return env


class TestPinning(unittest.TestCase):
    def test_pinned_model_constant(self):
        self.assertEqual(PINNED_MODEL, "glm-5.3-flash")

    def test_default_base_url_is_zai_coding_plan(self):
        self.assertEqual(DEFAULT_BASE_URL, "https://api.z.ai/api/coding/paas/v4")

    def test_alternative_model_rejected(self):
        with mock.patch.dict(os.environ, _clean_env(), clear=False):
            os.environ["AGENCY_ZAI_KEY"] = "k"
            os.environ["AGENCY_ZAI_MODEL"] = "gpt-4o"
            with self.assertRaises(RealModelNotConfigured):
                resolve_config()

    def test_pinned_model_accepted(self):
        env = _clean_env()
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ["AGENCY_ZAI_KEY"] = "k"
            os.environ.pop("AGENCY_ZAI_MODEL", None)
            cfg = resolve_config()
            self.assertEqual(cfg["model"], PINNED_MODEL)


class TestInertWithoutKey(unittest.TestCase):
    def test_missing_key_raises_not_configured(self):
        env = _clean_env()
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("AGENCY_ZAI_KEY", None)
            with self.assertRaises(RealModelNotConfigured):
                chat([{"role": "user", "content": "hi"}])

    def test_import_module_has_no_side_effects(self):
        # importing real_model must not require a key or network
        self.assertTrue(hasattr(real_model, "chat"))


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestBillingStop(unittest.TestCase):
    def _chat_with_status(self, code: int):
        env = _clean_env()
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ["AGENCY_ZAI_KEY"] = "k"
            err = urllib.error.HTTPError(
                url="x", code=code, msg="denied",
                hdrs=None, fp=io.BytesIO(b"billing problem"),
            )
            with mock.patch("agency_bench.real_model.urllib.request.urlopen", side_effect=err):
                with self.assertRaises(BillingError):
                    chat([{"role": "user", "content": "hi"}])

    def test_402_is_billing_stop(self):
        self._chat_with_status(402)

    def test_401_is_billing_stop(self):
        self._chat_with_status(401)

    def test_403_is_billing_stop(self):
        self._chat_with_status(403)

    def test_429_is_billing_stop(self):
        self._chat_with_status(429)

    def test_urlerror_is_billing_stop(self):
        env = _clean_env()
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ["AGENCY_ZAI_KEY"] = "k"
            err = urllib.error.URLError("conn refused")
            with mock.patch("agency_bench.real_model.urllib.request.urlopen", side_effect=err):
                with self.assertRaises(BillingError):
                    chat([{"role": "user", "content": "hi"}])

    def test_success_parses_content_and_usage(self):
        env = _clean_env()
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ["AGENCY_ZAI_KEY"] = "k"
            body = {
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"total_tokens": 7},
                "model": PINNED_MODEL,
            }
            with mock.patch(
                "agency_bench.real_model.urllib.request.urlopen",
                return_value=_FakeResponse(json.dumps(body).encode()),
            ):
                out = chat([{"role": "user", "content": "hi"}])
            self.assertEqual(out["content"], "hello")
            self.assertEqual(out["usage"]["total_tokens"], 7)


if __name__ == "__main__":
    unittest.main()
