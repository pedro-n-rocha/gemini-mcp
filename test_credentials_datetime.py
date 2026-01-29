import json
import os
import tempfile
import unittest


class TestCredentialsDatetime(unittest.TestCase):
    def test_get_session_accepts_offset_aware_expiry_string(self) -> None:
        # This regression test ensures we don't crash with:
        # "can't compare offset-naive and offset-aware datetimes"
        # when credentials.json stores an ISO timestamp with a timezone offset.
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_path = os.path.join(tmpdir, "credentials.json")
            with open(creds_path, "w") as f:
                json.dump(
                    {
                        "access_token": "test-access-token",
                        "refresh_token": None,
                        "client_id": "test-client-id",
                        "client_secret": "test-client-secret",
                        "scope": "openid email",
                        "expiry": "2099-01-01T00:00:00+00:00",
                    },
                    f,
                )

            prev = os.environ.get("CREDENTIALS_PATH")
            os.environ["CREDENTIALS_PATH"] = tmpdir
            try:
                from server import get_session

                token = get_session()
            finally:
                if prev is None:
                    os.environ.pop("CREDENTIALS_PATH", None)
                else:
                    os.environ["CREDENTIALS_PATH"] = prev

        self.assertEqual(token, "test-access-token")


if __name__ == "__main__":
    unittest.main()

