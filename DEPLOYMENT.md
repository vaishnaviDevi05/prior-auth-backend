# ☁️ Azure OpenAI Deployment Guide
# AI Prior Authorization Accelerator — 100% Azure-Native

---

## Architecture (No External APIs Needed)

```
┌─────────────────────────────────────────────────────────────┐
│                      Azure Cloud                            │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────┐               │
│  │  Azure App      │───▶│  Azure OpenAI    │               │
│  │  Service        │    │  (GPT-4o)        │               │
│  │  (Streamlit UI) │    │                  │               │
│  └─────────────────┘    └──────────────────┘               │
│          │                                                  │
│          ▼                                                  │
│  ┌─────────────────┐                                        │
│  │  Azure Key      │  (Stores API keys securely)            │
│  │  Vault          │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

Everything — the app, the AI model, the secrets — lives inside Azure.
No Anthropic key, no external AI APIs.

---

## STEP 1 — Create Azure OpenAI Resource

```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"

RESOURCE_GROUP="rg-prior-auth"
LOCATION="eastus"        # or: westeurope, australiaeast
AOI_NAME="oai-prior-auth-$(openssl rand -hex 4)"

az group create --name $RESOURCE_GROUP --location $LOCATION

az cognitiveservices account create \
  --name $AOI_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0 \
  --yes
```

---

## STEP 2 — Deploy GPT-4o Model

```bash
# Deploy gpt-4o (recommended) or gpt-4-turbo
az cognitiveservices account deployment create \
  --name $AOI_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "gpt-4o" \
  --model-name "gpt-4o" \
  --model-version "2024-08-06" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"

# Get your endpoint and key
ENDPOINT=$(az cognitiveservices account show \
  --name $AOI_NAME --resource-group $RESOURCE_GROUP \
  --query properties.endpoint --output tsv)

API_KEY=$(az cognitiveservices account keys list \
  --name $AOI_NAME --resource-group $RESOURCE_GROUP \
  --query key1 --output tsv)

echo "Endpoint: $ENDPOINT"
echo "Key:      $API_KEY"
```

---

## STEP 3 — Store Keys in Azure Key Vault

```bash
KV_NAME="kv-priorauth-$(openssl rand -hex 4)"

az keyvault create \
  --name $KV_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

az keyvault secret set --vault-name $KV_NAME --name "AZURE-OPENAI-ENDPOINT" --value "$ENDPOINT"
az keyvault secret set --vault-name $KV_NAME --name "AZURE-OPENAI-API-KEY"  --value "$API_KEY"
```

---

## STEP 4 — Create Azure App Service

```bash
APP_NAME="prior-auth-ai-$(openssl rand -hex 4)"

az appservice plan create \
  --name "asp-prior-auth" \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku B1 \
  --is-linux

az webapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan "asp-prior-auth" \
  --runtime "PYTHON:3.11"

# Enable managed identity (so App Service can read Key Vault)
PRINCIPAL_ID=$(az webapp identity assign \
  --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --query principalId --output tsv)

az keyvault set-policy \
  --name $KV_NAME \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

---

## STEP 5 — Configure App Settings (Key Vault References)

```bash
# These reference Key Vault — the actual keys are NEVER stored in App Service
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    AZURE_OPENAI_ENDPOINT="@Microsoft.KeyVault(VaultName=${KV_NAME};SecretName=AZURE-OPENAI-ENDPOINT)" \
    AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(VaultName=${KV_NAME};SecretName=AZURE-OPENAI-API-KEY)" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    AZURE_OPENAI_API_VERSION="2024-08-01-preview"
```

---

## STEP 6 — Set Startup Command & Deploy

```bash
az webapp config set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "startup.sh"

# Deploy (from your project folder)
zip -r deploy.zip . --exclude "*.pyc" --exclude ".git/*"

az webapp deploy \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --src-path deploy.zip \
  --type zip

# Get app URL
echo "App URL: https://$(az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query defaultHostName --output tsv)"
```

---

## Running Locally (for testing)

```bash
pip install streamlit openai

export AZURE_OPENAI_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-key-from-azure-portal"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
export AZURE_OPENAI_API_VERSION="2024-08-01-preview"

streamlit run frontend/app.py
# → Open http://localhost:8501
```

If you skip the env vars, the app runs in **Demo Mode** with mock data — useful for UI testing.

---

## File Reference

```
prior-auth-app/
├── app.py              ← Main Streamlit app (Azure OpenAI powered)
├── requirements.txt    ← openai + streamlit only
├── Procfile            ← Process definition
├── runtime.txt         ← Python 3.11
├── startup.sh          ← Azure App Service startup script
└── DEPLOYMENT.md       ← This file
```

---

## Monthly Cost Estimate

| Service | SKU | Est. Cost |
|---------|-----|-----------|
| Azure App Service | B1 Linux | ~$13/mo |
| Azure OpenAI (GPT-4o) | Pay-per-token | ~$5–30/mo depending on usage |
| Azure Key Vault | Standard | ~$0.03/10K ops |
| **Total** | | **~$20–45/mo** |
