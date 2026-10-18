"""Create the user-authorized GitHub forks after `gh auth login`.

No tokens are read or printed. Existing unrelated repositories are never changed.
"""
import json
import subprocess
from pathlib import Path


def main():
    manifest_path = Path(__file__).resolve().parents[1] / "docs/upstreams.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profile = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True)
    if profile.returncode or profile.stdout.strip() != manifest["github_account"]:
        raise SystemExit("Log in to GitHub CLI as Cyberchopin first: gh auth login")
    failed = []
    for repo in manifest["repositories"]:
        destination = manifest["github_account"] + "/" + repo["repository"].split("/")[1]
        result = subprocess.run(["gh", "repo", "fork", repo["repository"], "--clone=false", "--remote=false"], capture_output=True, text=True)
        verify = subprocess.run(["gh", "api", "repos/" + destination], capture_output=True, text=True)
        try:
            data = json.loads(verify.stdout)
        except ValueError:
            data = {}
        if verify.returncode == 0 and data.get("fork") and data.get("parent", {}).get("full_name", "").lower() == repo["repository"].lower():
            repo["github_fork_created"] = True
            repo["fork_url"] = "https://github.com/" + destination
            print("Verified fork: " + destination)
        else:
            failed.append(repo["repository"])
            print("Could not verify fork: " + repo["repository"])
        manifest_path.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    if not failed:
        manifest["fork_blocker"] = None
        manifest_path.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
