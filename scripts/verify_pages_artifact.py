"""Verify the uploaded artifact in this run before allowing Pages deployment.

Credentials come only from the environment and are never logged. This checks
GitHub's artifact API; it does not claim that the later Pages deployment succeeded.
"""
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def verify(repository, run_id, artifact_id, token, api_url='https://api.github.com', attempts=5):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repository):
        raise ValueError('Invalid GitHub repository identifier')
    if not str(run_id).isdigit() or not str(artifact_id).isdigit():
        raise ValueError('Missing or invalid workflow run / uploaded artifact ID')
    if not token:
        raise ValueError('Missing GitHub token for artifact verification')
    endpoint = (f'{api_url.rstrip("/")}/repos/{repository}/actions/runs/{run_id}'
                '/artifacts?name=github-pages&per_page=100')
    reason = 'Artifact has not appeared in this workflow run'
    for attempt in range(1, attempts + 1):
        try:
            request = Request(endpoint, headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
                'User-Agent': 'AurumLab-Pages-verification',
            })
            with urlopen(request, timeout=20) as response:
                data = json.load(response)
            candidates = [a for a in data['artifacts']
                          if a['name'] == 'github-pages' and not a['expired']]
            if len(candidates) > 1:
                raise RuntimeError('Multiple active github-pages artifacts exist in this run; deployment would be ambiguous')
            if candidates:
                artifact = candidates[0]
                if str(artifact['id']) == str(artifact_id) and artifact['size_in_bytes'] > 0:
                    print(f'Verified github-pages artifact ID {artifact_id}: '
                          f'{artifact["size_in_bytes"]} bytes, workflow run {run_id}', flush=True)
                    return artifact
                reason = 'Visible artifact ID differs from upload output, or its size is zero'
            else:
                reason = 'No active github-pages artifact is visible in this workflow run'
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise RuntimeError(f'Artifact API returned HTTP {exc.code}; verify actions: read permission and API rate limits') from None
            if exc.code not in (404, 408, 429, 500, 502, 503, 504):
                raise RuntimeError(f'Artifact API returned HTTP {exc.code}') from None
            reason = f'Artifact API returned HTTP {exc.code}'
        except (URLError, TimeoutError, ConnectionError):
            reason = 'Artifact API connection failed or timed out'
        if attempt < attempts:
            print(f'::warning::{reason}; retrying verification ({attempt}/{attempts})', flush=True)
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f'{reason}. Expected artifact ID {artifact_id}, run {run_id}. '
                       'Check the Upload static site log for an upload ID and retention status.')


if __name__ == '__main__':
    verify(os.environ.get('GITHUB_REPOSITORY', ''),
           os.environ.get('GITHUB_RUN_ID', ''),
           os.environ.get('EXPECTED_ARTIFACT_ID', ''),
           os.environ.get('GH_TOKEN', ''),
           os.environ.get('GITHUB_API_URL', 'https://api.github.com'))
