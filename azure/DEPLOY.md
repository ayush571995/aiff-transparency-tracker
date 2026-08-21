# Deploying to Azure (using your subscription credits)

Azure CLI isn't installed/authenticated in the sandbox this was built in, so these are the
exact steps for **you** to run — either in your own terminal (after `winget install
Microsoft.AzureCLI` or `az` already installed) or via Cloud Shell at portal.azure.com.
None of this needs anything beyond what's already in this repo.

## 0. Push this repo to GitHub first

```powershell
cd "C:\Users\Ayush Saluja\OneDrive\Desktop\projects\webapp\aiff"
gh repo create aiff-transparency-tracker --public --source=. --remote=origin
git push -u origin main
```

(If you don't have `gh`, create the repo manually on github.com and `git remote add origin <url>`.)

## 1. Log in and pick your subscription

```powershell
az login
az account list --output table
az account set --subscription "<your-subscription-name-or-id>"
```

## 2. Create a resource group (skip if you already have one you want to use)

```powershell
az group create --name rg-aiff-tracker --location centralus
```

## 3. Deploy the Static Web App via the Bicep template

This creates the resource **and** links it to your GitHub repo in one step — Azure will ask
you to authorize a GitHub connection interactively the first time.

```powershell
az deployment group create `
  --resource-group rg-aiff-tracker `
  --template-file azure/staticwebapp.bicep `
  --parameters repositoryUrl="https://github.com/<your-username>/aiff-transparency-tracker" branch="main"
```

Alternatively, without Bicep, the one-liner (also prompts for GitHub auth):

```powershell
az staticwebapp create `
  --name roadto-fifa-wc-aiff-tracker `
  --resource-group rg-aiff-tracker `
  --source "https://github.com/<your-username>/aiff-transparency-tracker" `
  --location centralus `
  --branch main `
  --app-location "site" `
  --output-location "" `
  --login-with-github
```

> Note: `--login-with-github` / the Bicep `repositoryUrl` path makes Azure generate **its own**
> deploy workflow file. Since this repo already ships `.github/workflows/deploy.yml`, either:
> (a) let Azure add its workflow and delete ours, or
> (b) create the Static Web App **without** linking a repo (omit `--source`), then manually add
> the deployment token as a GitHub secret (step 4) and keep our workflow. (b) is what the rest
> of this doc assumes, since our workflow already matches the app's config exactly.

To create it *without* auto-linking (recommended, matches our workflow):

```powershell
az staticwebapp create `
  --name roadto-fifa-wc-aiff-tracker `
  --resource-group rg-aiff-tracker `
  --location centralus `
  --sku Free
```

## 4. Get the deployment token and add it to GitHub

```powershell
az staticwebapp secrets list `
  --name roadto-fifa-wc-aiff-tracker `
  --resource-group rg-aiff-tracker `
  --query "properties.apiKey" -o tsv
```

Copy that token, then in your GitHub repo: **Settings → Secrets and variables → Actions → New
repository secret**, name it `AZURE_STATIC_WEB_APPS_API_TOKEN`, paste the value.

Push to `main` (or re-run the "Deploy to Azure Static Web Apps" workflow from the Actions tab) —
`deploy.yml` will pick it up and deploy `site/` as-is.

## 5. Get your free `*.azurestaticapps.net` URL

```powershell
az staticwebapp show `
  --name roadto-fifa-wc-aiff-tracker `
  --resource-group rg-aiff-tracker `
  --query "defaultHostname" -o tsv
```

The site is live at `https://<that-hostname>` within a minute or two of the first successful
Action run. Share/test with this before pointing a custom domain at it.

## 6. Point roadtowc34football at it (once you own the domain)

Once you've bought the domain from a registrar (Namecheap, GoDaddy, Cloudflare, IN Registry for
`.in`, etc. — that purchase is on you, I can't do it for you):

```powershell
az staticwebapp hostname set `
  --name roadto-fifa-wc-aiff-tracker `
  --resource-group rg-aiff-tracker `
  --hostname roadtowc34football.com
```

Azure will give you a DNS record (usually a `CNAME` for a subdomain, or `TXT` + `A`/`ALIAS` for
an apex/root domain) to add at your registrar. Free SSL certificate is issued automatically once
DNS validates — typically within minutes to a few hours.

## Cost

Static Web Apps **Free** tier: 100 GB bandwidth/month, free custom domain + SSL, 2 free custom
domains, no compute cost since there's no server — just static files. This should cost close to
$0 of your credits even with meaningful traffic. If you ever add a real backend/API, that's a
separate (Functions/App Service) cost — not needed for this project as designed.
