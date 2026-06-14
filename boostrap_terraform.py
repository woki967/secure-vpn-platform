import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise FileNotFoundError(name)
    return path


def build_command(name: str, *args: str) -> list[str]:
    executable = resolve_executable(name)
    if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/c", executable, *args]
    return [executable, *args]


SUBPROCESS_TEXT_KW = {
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}


def run_command(
    name: str,
    *args: str,
    check: bool = False,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        build_command(name, *args),
        check=check,
        capture_output=capture_output,
        **SUBPROCESS_TEXT_KW,
    )


def capture_command(name: str, *args: str) -> str:
    return subprocess.check_output(
        build_command(name, *args),
        **SUBPROCESS_TEXT_KW,
    ).strip()


def check_required_tools() -> None:
    missing = [
        tool
        for tool in ("git", "az")
        if not shutil.which(tool)
    ]

    if missing:
        print("ERROR: Missing required tools in PATH:")
        for tool in missing:
            print(f"  - {tool}")

        if os.name == "nt":
            print()
            print(
                "On Windows install Git and Azure CLI, "
                "then open a new terminal."
            )

        sys.exit(1)


def has_staged_changes(path: str) -> bool:
    result = run_command(
        "git",
        "diff",
        "--cached",
        "--quiet",
        "--",
        path,
        capture_output=True,
    )
    return result.returncode != 0


def push_backend_tf(backend_file: Path) -> None:
    backend_path = "terraform/backend.tf"

    if not backend_file.exists():
        print(f"ERROR: {backend_path} not found.")
        sys.exit(1)

    print()
    print("Committing backend.tf...")

    run_command(
        "git",
        "add",
        "--",
        backend_path,
        check=True,
    )

    if not has_staged_changes(backend_path):
        print()
        print(
            f"{backend_path} is already committed "
            "and unchanged in the repository."
        )
        print("Skipping commit and push.")
        return

    run_command(
        "git",
        "commit",
        "-m",
        "Configure terraform backend",
        check=True,
    )

    run_command(
        "git",
        "push",
        check=True,
    )

    print("backend.tf pushed successfully.")


def main() -> None:
    print("=== Terraform Bootstrap ===")

    check_required_tools()

    try:
        remote_url = capture_command(
            "git",
            "remote",
            "get-url",
            "origin",
        )
    except Exception:
        print("ERROR: Not a git repository.")
        sys.exit(1)

    print(f"Git remote: {remote_url}")

    if remote_url.startswith("git@github.com:"):
        repo_path = remote_url.replace(
            "git@github.com:",
            "",
        ).replace(
            ".git",
            "",
        )
    elif remote_url.startswith("https://github.com/"):
        repo_path = remote_url.replace(
            "https://github.com/",
            "",
        ).replace(
            ".git",
            "",
        )
    else:
        print("ERROR: Unsupported GitHub URL.")
        sys.exit(1)

    owner, repo = repo_path.split("/")

    print()
    print("Detected Repository")
    print(f"Owner: {owner}")
    print(f"Repository: {repo}")

    print()
    print("Checking Azure login...")

    try:
        account_json = capture_command(
            "az",
            "account",
            "show",
            "--output",
            "json",
        )
    except Exception:
        print()
        print("ERROR: Azure CLI is not logged in.")
        print("Run: az login")
        sys.exit(1)

    account = json.loads(account_json)

    subscription_id = account["id"]
    tenant_id = account["tenantId"]
    subscription_name = account["name"]

    print()
    print("Azure Account")
    print(f"Subscription: {subscription_name}")
    print(f"Subscription ID: {subscription_id}")
    print(f"Tenant ID: {tenant_id}")

    print()
    print("Checking Terraform State Resource Group...")

    state_rg = "rg-terraform-state"

    result = run_command(
        "az",
        "group",
        "exists",
        "--name",
        state_rg,
        capture_output=True,
    )

    rg_exists = result.stdout.strip().lower() == "true"

    if rg_exists:
        print(f"Resource Group exists: {state_rg}")
    else:
        print(f"Resource Group does not exist: {state_rg}")

        answer = input(
            "Create Resource Group? [Y/n]: "
        ).strip().lower()

        if answer not in ["", "y", "yes"]:
            print("Bootstrap cancelled.")
            sys.exit(0)

        print()
        print("Creating Resource Group...")

        run_command(
            "az",
            "group",
            "create",
            "--name",
            state_rg,
            "--location",
            "polandcentral",
            check=True,
        )

        print(f"Resource Group created: {state_rg}")

    print()
    print("Checking Storage Accounts...")

    storage_accounts_json = capture_command(
        "az",
        "storage",
        "account",
        "list",
        "--resource-group",
        state_rg,
        "--output",
        "json",
    )

    storage_accounts = json.loads(storage_accounts_json)

    if len(storage_accounts) == 1:
        storage_account_name = storage_accounts[0]["name"]

        print()
        print(
            f"Using Storage Account: "
            f"{storage_account_name}"
        )
    elif len(storage_accounts) > 1:
        print()
        print("Multiple Storage Accounts found:")

        for index, account_item in enumerate(
            storage_accounts,
            start=1,
        ):
            print(f"[{index}] {account_item['name']}")

        choice = int(input("Select Storage Account: "))
        storage_account_name = storage_accounts[choice - 1]["name"]
    else:
        print()
        print("No Storage Account found.")

        create = input(
            "Create Storage Account? [Y/n]: "
        ).strip().lower()

        if create not in ["", "y", "yes"]:
            print("Bootstrap cancelled.")
            sys.exit(0)

        random_suffix = secrets.token_hex(4)
        storage_account_name = f"tfstate{random_suffix}"

        print()
        print(
            f"Creating Storage Account: "
            f"{storage_account_name}"
        )

        run_command(
            "az",
            "storage",
            "account",
            "create",
            "--name",
            storage_account_name,
            "--resource-group",
            state_rg,
            "--location",
            "polandcentral",
            "--sku",
            "Standard_LRS",
            check=True,
        )

        print("Storage Account created.")

    print()
    print("Checking tfstate container...")

    container_name = "tfstate"

    container_exists = run_command(
        "az",
        "storage",
        "container",
        "exists",
        "--name",
        container_name,
        "--account-name",
        storage_account_name,
        "--auth-mode",
        "login",
        "--output",
        "json",
        capture_output=True,
    )

    container_data = json.loads(container_exists.stdout)

    if container_data["exists"]:
        print(f"Container exists: {container_name}")
    else:
        print(f"Container does not exist: {container_name}")
        print("Creating container...")

        run_command(
            "az",
            "storage",
            "container",
            "create",
            "--name",
            container_name,
            "--account-name",
            storage_account_name,
            "--auth-mode",
            "login",
            check=True,
        )

        print("Container created.")

    print()
    print("Generating backend.tf...")

    terraform_dir = Path("terraform")
    terraform_dir.mkdir(exist_ok=True)

    backend_file = terraform_dir / "backend.tf"

    backend_content = f'''terraform {{
  backend "azurerm" {{
    resource_group_name  = "{state_rg}"
    storage_account_name = "{storage_account_name}"
    container_name       = "{container_name}"
    key                  = "{repo}.tfstate"
  }}
}}
'''

    backend_file.write_text(
        backend_content,
        encoding="utf-8",
    )

    print(f"Created: {backend_file}")

    print()
    print("Generating SSH keypair...")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    private_key_path = output_dir / "id_ed25519"
    public_key_path = output_dir / "id_ed25519.pub"

    if private_key_path.exists():
        print("SSH key already exists.")
    else:
        if not shutil.which("ssh-keygen"):
            print("ERROR: ssh-keygen not found.")
            if os.name == "nt":
                print(
                    "On Windows enable OpenSSH Client in "
                    "Settings -> Apps -> Optional features."
                )
            sys.exit(1)

        run_command(
            "ssh-keygen",
            "-t",
            "ed25519",
            "-N",
            "",
            "-f",
            str(private_key_path.resolve()),
            check=True,
        )

        print("SSH keypair generated.")

    print()
    print("Checking App Registration...")

    app_name = f"{repo}-github-actions"

    apps_json = capture_command(
        "az",
        "ad",
        "app",
        "list",
        "--display-name",
        app_name,
        "--output",
        "json",
    )

    apps = json.loads(apps_json)

    if apps:
        app = apps[0]
        client_id = app["appId"]

        print(f"Using existing App Registration: {app_name}")
        print(f"Client ID: {client_id}")
    else:
        print(f"Creating App Registration: {app_name}")

        created_app_json = capture_command(
            "az",
            "ad",
            "app",
            "create",
            "--display-name",
            app_name,
            "--output",
            "json",
        )

        created_app = json.loads(created_app_json)
        client_id = created_app["appId"]

        print(f"Created App Registration: {app_name}")
        print(f"Client ID: {client_id}")

    print()
    print("Checking Service Principal...")

    sp_json = capture_command(
        "az",
        "ad",
        "sp",
        "list",
        "--filter",
        f"appId eq '{client_id}'",
        "--output",
        "json",
    )

    service_principals = json.loads(sp_json)

    if service_principals:
        print("Using existing Service Principal.")
    else:
        print("Creating Service Principal...")

        run_command(
            "az",
            "ad",
            "sp",
            "create",
            "--id",
            client_id,
            check=True,
        )

        print("Service Principal created.")

    print()
    print("Checking Contributor role assignment...")

    role_json = capture_command(
        "az",
        "role",
        "assignment",
        "list",
        "--assignee",
        client_id,
        "--scope",
        f"/subscriptions/{subscription_id}",
        "--output",
        "json",
    )

    roles = json.loads(role_json)

    contributor_exists = any(
        role["roleDefinitionName"] == "Contributor"
        for role in roles
    )

    if contributor_exists:
        print("Contributor role already assigned.")
    else:
        print("Assigning Contributor role...")

        run_command(
            "az",
            "role",
            "assignment",
            "create",
            "--assignee",
            client_id,
            "--role",
            "Contributor",
            "--scope",
            f"/subscriptions/{subscription_id}",
            check=True,
        )

        print("Contributor role assigned.")

    print()
    print("Checking Federated Credential...")

    credential_name = "github-actions"

    credential_json = capture_command(
        "az",
        "ad",
        "app",
        "federated-credential",
        "list",
        "--id",
        client_id,
        "--output",
        "json",
    )

    credentials = json.loads(credential_json)

    credential_exists = any(
        credential["name"] == credential_name
        for credential in credentials
    )

    if credential_exists:
        print("Federated Credential already exists.")
    else:
        print("Creating Federated Credential...")

        federation_config = {
            "name": credential_name,
            "issuer": "https://token.actions.githubusercontent.com",
            "subject": f"repo:{owner}/{repo}:ref:refs/heads/main",
            "audiences": ["api://AzureADTokenExchange"],
        }

        config_file = output_dir / "federation.json"

        config_file.write_text(
            json.dumps(federation_config, indent=2),
            encoding="utf-8",
        )

        run_command(
            "az",
            "ad",
            "app",
            "federated-credential",
            "create",
            "--id",
            client_id,
            "--parameters",
            str(config_file.resolve()),
            check=True,
        )

        print("Federated Credential created.")

    print()
    print("=" * 50)
    print("GITHUB VARIABLES")
    print("=" * 50)

    public_key = public_key_path.read_text(
        encoding="utf-8",
    ).strip()

    print()
    print(f"AZURE_CLIENT_ID={client_id}")
    print(f"AZURE_TENANT_ID={tenant_id}")
    print(f"AZURE_SUBSCRIPTION_ID={subscription_id}")
    print(f"SSH_PUBLIC_KEY={public_key}")

    print()
    print("=" * 50)
    print("GITHUB SECRETS")
    print("=" * 50)

    private_key = private_key_path.read_text(encoding="utf-8")

    print()
    print("SSH_PRIVATE_KEY=")
    print(private_key)

    print()
    print("Creating bootstrap summary...")

    summary_file = output_dir / "bootstrap-summary.txt"

    summary_content = f"""
========================================
GITHUB VARIABLES
========================================

AZURE_CLIENT_ID={client_id}

AZURE_TENANT_ID={tenant_id}

AZURE_SUBSCRIPTION_ID={subscription_id}

SSH_PUBLIC_KEY={public_key}

========================================
GITHUB SECRETS
========================================

SSH_PRIVATE_KEY

Use content from:

{private_key_path}

========================================
BACKEND
========================================

terraform/backend.tf

========================================
"""

    summary_file.write_text(
        summary_content,
        encoding="utf-8",
    )

    print(f"Created: {summary_file}")
    print()

    push_backend = input(
        "Push backend.tf to repository? [Y/n]: "
    ).strip().lower()

    if push_backend in ["", "y", "yes"]:
        push_backend_tf(backend_file)
    else:
        print()
        print(
            "Pominięto wysyłkę backend.tf do repozytorium."
        )
        print()
        print(
            "Ręcznie przekaż plik do zdalnego repozytorium:"
        )
        print(f"  Lokalny plik: {backend_file.resolve()}")
        print(
            "  Docelowa ścieżka w repo: terraform/backend.tf"
        )
        print()
        print(
            "Bez tego pliku workflowy GitHub Actions "
            "nie połączą się ze stanem Terraform."
        )


if __name__ == "__main__":
    main()
