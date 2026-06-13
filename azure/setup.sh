#!/usr/bin/env bash
# ===========================================================================
# azure/setup.sh
#
# WHAT: Provisions every Azure resource Phase 1 needs, via the Azure CLI.
# WHY:  Infrastructure-as-code. Anyone can recreate the whole cloud footprint
#       by running one script — no clicking around the portal, fully repeatable.
#
# PREREQUISITES:
#   1. Install Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli
#      (macOS: `brew install azure-cli`)
#   2. Log in:            az login
#
# USAGE:   bash azure/setup.sh
#
# NOTE: Resource/storage account names must be GLOBALLY unique across Azure.
#       If creation fails with "already taken", change the names below.
#       `set -euo pipefail` makes the script stop on the first error instead of
#       barreling ahead.
# ===========================================================================
set -euo pipefail

# --- Configuration (edit these once) ---------------------------------------
RESOURCE_GROUP="rg-macromarket-elt"
LOCATION="eastus2"                 # same region as Snowflake -> no egress fees
STORAGE_ACCOUNT="macromarketelt"   # 3-24 chars, lowercase+digits, GLOBALLY unique
CONTAINER="raw-data"               # the ADLS "filesystem"
KEY_VAULT="kv-macromarket"         # GLOBALLY unique
DATA_FACTORY="adf-macromarket"

# Subfolders inside the container, one per data source (created as empty dirs).
DIRS=( "stock-prices" "stock-fundamentals" "fred-series" "crypto-prices" "fear-greed" "news-headlines" )

echo "==> 1/6 Resource group"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "==> 2/6 ADLS Gen2 storage account (--hns true = hierarchical namespace)"
# --hns true is THE flag that turns plain Blob Storage into ADLS Gen2 (real
# directories + directory-level ACLs). Standard_LRS = cheapest redundancy.
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hns true \
  --access-tier Hot

echo "==> 3/6 Container + source subfolders"
az storage fs create --name "$CONTAINER" --account-name "$STORAGE_ACCOUNT"
for d in "${DIRS[@]}"; do
  az storage fs directory create --name "$d" --file-system "$CONTAINER" --account-name "$STORAGE_ACCOUNT"
done

echo "==> 4/6 Key Vault + secrets"
az keyvault create --name "$KEY_VAULT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"
# Placeholder secrets — replace the values once Snowflake + FRED keys exist.
az keyvault secret set --vault-name "$KEY_VAULT" --name snowflake-account  --value "REPLACE_ME"
az keyvault secret set --vault-name "$KEY_VAULT" --name snowflake-user     --value "REPLACE_ME"
az keyvault secret set --vault-name "$KEY_VAULT" --name snowflake-password --value "REPLACE_ME"
az keyvault secret set --vault-name "$KEY_VAULT" --name fred-api-key       --value "REPLACE_ME"

echo "==> 5/7 Outputs you'll need for local dev + Snowflake stage"
echo "--- ADLS connection string (paste into .env as AZURE_STORAGE_CONNECTION_STRING) ---"
# The Python uploader uses this to authenticate to ADLS from your laptop.
az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --output tsv

echo "--- Azure tenant ID (paste into snowflake/setup/06_...sql as AZURE_TENANT_ID) ---"
# Not a secret — just an identifier for your Azure AD tenant. The Snowflake
# storage integration needs it to know which directory to trust.
az account show --query tenantId --output tsv

echo "==> 6/7 Data Factory (orchestrator, configured in Phase 7)"
az datafactory create --name "$DATA_FACTORY" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"

echo ""
echo "==> 7/7 (MANUAL, do AFTER Snowflake) Grant Snowflake's app read access"
cat <<'NOTE'
The storage integration uses an Azure AD app that Snowflake creates for you.
You can only do this step AFTER running snowflake/setup/06_...sql, because
Snowflake gives you the app name in the DESC STORAGE INTEGRATION output.

  1. In Snowflake:  DESC STORAGE INTEGRATION azure_adls_integration;
     - open AZURE_CONSENT_URL in a browser and click Accept
     - copy AZURE_MULTI_TENANT_APP_NAME  (looks like:  <name>_<number>)

  2. Find that app's service principal object id, then assign it read access:

     APP_NAME="<paste AZURE_MULTI_TENANT_APP_NAME, the part before the underscore>"
     SP_ID=$(az ad sp list --display-name "$APP_NAME" --query "[0].id" -o tsv)
     STORAGE_ID=$(az storage account show -n macromarketelt -g rg-macromarket-elt --query id -o tsv)
     az role assignment create \
       --assignee "$SP_ID" \
       --role "Storage Blob Data Reader" \
       --scope "$STORAGE_ID"

  3. Back in Snowflake:  LIST @MACROMARKET.BRONZE.adls_raw_stage;  (should succeed)
NOTE

echo ""
echo "DONE. Next: copy the connection string into .env and the tenant ID into SQL file 06."
