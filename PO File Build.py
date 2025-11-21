import csv
import os
import re
import tempfile
from pathlib import Path
from pathlib import Path
from azure.storage.fileshare import ShareServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# ==========================
# CONFIGURATION
# ==========================

# Azure Storage account info
STORAGE_ACCOUNT_NAME = "productioneu2integration"  # e.g. "lewisstorageacct"

# Name of the file share
FILE_SHARE_NAME = "finance-integrations/NONPROD/OUT/Concur"

# Key Vault Settings
KEY_VAULT_URL = "https://lts-eu2-dev-py-apps-kv.vault.azure.net/"
SECRET_NAME = "Concur-PO-Storage-Account-Key"

# Paths *within* the file share for your files
PATH_300 = "300 rows.csv"
PATH_210_220 = "210 and 220 rows.csv"
PATH_200 = "200 rows.csv"
PATH_OUTPUT = "combined_by_po_300_210_220_200.csv"

# Local temp directory for processing
LOCAL_TEMP_DIR = Path(tempfile.gettempdir()) / "concur"  # change as needed

def get_storage_account_key() -> str:
    """
    Fetch the storage account key from Azure Key Vault.
    Uses DefaultAzureCredential, so it works with:
      - Azure CLI login (local dev)
      - VS Code login
      - Managed Identity (VM, Function, etc.)
    """
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
    secret = secret_client.get_secret(SECRET_NAME)
    return secret.value


def record_type_order(record_type: str) -> int:
    rt = record_type.strip()
    if rt == "300":
        return 1
    if rt == "210":
        return 2
    if rt == "220":
        return 3
    if rt == "200":
        return 4
    return 99  # unexpected types go last


def read_csv_rows(path: Path):
    """Yield non-empty rows from a CSV file."""
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or all(col.strip() == "" for col in row):
                continue
            yield row


def download_file_from_share(share_client, remote_path: str, local_path: Path):
    """Download a file from Azure File Share to local disk."""
    file_client = share_client.get_file_client(remote_path)
    with open(local_path, "wb") as f:
        data = file_client.download_file()
        f.write(data.readall())


def upload_file_to_share(share_client, local_path: Path, remote_path: str):
    """Upload a local file to Azure File Share."""
    file_client = share_client.get_file_client(remote_path)

    # Ensure any parent "directories" exist in the share path (if you use subfolders)
    directory = os.path.dirname(remote_path)
    if directory:
        dir_client = share_client.get_directory_client(directory)
        try:
            dir_client.create_directory()
        except Exception:
            # directory may already exist; ignore
            pass

    with open(local_path, "rb") as f:
        file_client.upload_file(f)


def main():
    # Make sure temp directory exists
    LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Build local paths
    local_300 = LOCAL_TEMP_DIR / "300 rows.csv"
    local_210_220 = LOCAL_TEMP_DIR / "210 and 220 rows.csv"
    local_200 = LOCAL_TEMP_DIR / "200 rows.csv"
    local_output = LOCAL_TEMP_DIR / "combined_by_po_300_210_220_200.csv"

    # Connect to the file share
    storage_key = get_storage_account_key()

    service_client = ShareServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT_NAME}.file.core.windows.net/",
        credential=storage_key,
    )
    share_client = service_client.get_share_client(FILE_SHARE_NAME)

    # ==========================
    # 1) Download input files
    # ==========================
    download_file_from_share(share_client, PATH_300, local_300)
    download_file_from_share(share_client, PATH_210_220, local_210_220)
    download_file_from_share(share_client, PATH_200, local_200)

    # ==========================
    # 2) Combine rows by PO / record type
    # ==========================
    all_rows = []
    seq = 0
    # Simple counters for sanity check
    total_rows_seen = 0

    


    for path in [local_300, local_210_220, local_200]:
        if not path.exists():
            print(f"WARNING: {path} does not exist, skipping.")
            continue

        for row in read_csv_rows(path):
            total_rows_seen += 1
            # Column 0 should contain the PO, but may have BOM / junk
            po_raw = row[0]

            # Strip BOM variants
            po_clean = po_raw.replace("\ufeff", "").replace("ï»¿", "").strip()

            # Try to extract the first run of digits as PO number
            m = re.search(r"\d+", po_clean)
            if m:
                po_number_str = m.group(0)
                try:
                    po_number = int(po_number_str)
                except ValueError:
                    # Very unlikely, but just in case
                    print(f"Warning: couldn't parse PO after cleaning: {repr(po_clean)} from row {row}")
                    po_number = 999999999  # push to end
            else:
                # No digits at all – keep the row, but at the end
                print(f"Warning: no digits found in PO column, keeping row at end: {row}")
                po_number = 999999999

            record_type = row[3].strip() if len(row) > 3 else ""
            rt_ord = record_type_order(record_type)

            all_rows.append((po_number, rt_ord, seq, row))
            seq += 1

    print(f"Total rows processed from all input files: {total_rows_seen}")
    print(f"Total rows in output: {len(all_rows)}")

    all_rows.sort(key=lambda x: (x[0], x[1], x[2]))

    with local_output.open("w", newline="") as out_f:
        writer = csv.writer(out_f)
        for _, _, _, row in all_rows:
            writer.writerow(row)

    print(f"Combined file created locally at: {local_output}")

    # ==========================
    # 3) Upload result back to Azure File Share
    # ==========================
    upload_file_to_share(share_client, local_output, PATH_OUTPUT)
    print(f"Uploaded combined file to share '{FILE_SHARE_NAME}' as '{PATH_OUTPUT}'")


if __name__ == "__main__":
    main()
