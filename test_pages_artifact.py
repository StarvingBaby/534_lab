import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.verify_pages_artifact import verify


def response(artifacts):
    return io.BytesIO(json.dumps({'artifacts': artifacts}).encode())


GOOD = {'id': 42, 'name': 'github-pages', 'expired': False, 'size_in_bytes': 100}


class PagesArtifactTests(unittest.TestCase):
    def test_upload_visible_after_indexing_delay(self):
        with patch('scripts.verify_pages_artifact.urlopen', side_effect=[response([]), response([GOOD])]) as call, patch('scripts.verify_pages_artifact.time.sleep') as sleep:
            self.assertEqual(verify('owner/repo', '123', '42', 'test-only-token'), GOOD)
            self.assertEqual(call.call_count, 2)
            sleep.assert_called_once_with(2)

    def test_missing_upload_output_fails_before_api_call(self):
        with patch('scripts.verify_pages_artifact.urlopen') as call:
            with self.assertRaisesRegex(ValueError, 'artifact ID'):
                verify('owner/repo', '123', '', 'test-only-token')
            call.assert_not_called()

    def test_expired_empty_wrong_id_and_missing_artifacts_fail(self):
        for artifact in [None, {**GOOD, 'expired': True}, {**GOOD, 'size_in_bytes': 0}, {**GOOD, 'id': 43}]:
            with self.subTest(artifact=artifact), patch('scripts.verify_pages_artifact.urlopen', return_value=response([] if artifact is None else [artifact])):
                with self.assertRaisesRegex(RuntimeError, 'Expected artifact ID 42'):
                    verify('owner/repo', '123', '42', 'test-only-token', attempts=1)

    def test_duplicate_names_are_rejected(self):
        with patch('scripts.verify_pages_artifact.urlopen', return_value=response([GOOD, {**GOOD, 'id': 43}])):
            with self.assertRaisesRegex(RuntimeError, 'Multiple active'):
                verify('owner/repo', '123', '42', 'test-only-token')

    def test_permission_error_is_actionable_without_retry(self):
        with patch('scripts.verify_pages_artifact.urlopen', side_effect=HTTPError('test', 403, 'Forbidden', {}, None)), patch('scripts.verify_pages_artifact.time.sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'actions: read'):
                verify('owner/repo', '123', '42', 'test-only-token')
            sleep.assert_not_called()

    def test_transient_api_failure_is_retried(self):
        with patch('scripts.verify_pages_artifact.urlopen', side_effect=[HTTPError('test', 503, 'Unavailable', {}, None), response([GOOD])]), patch('scripts.verify_pages_artifact.time.sleep'):
            self.assertEqual(verify('owner/repo', '123', '42', 'test-only-token'), GOOD)


if __name__ == '__main__':
    unittest.main()
