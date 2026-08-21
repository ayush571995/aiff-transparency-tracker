// Provisions a single Azure Static Web App on the Free tier.
// Free tier includes: 100 GB bandwidth/month, free SSL, custom domain support —
// comfortably enough for a low-traffic public-interest tracker like this one.
param name string = 'road-to-wc34-aiff-tracker'
param location string = 'centralus' // Static Web Apps is only available in a subset of regions
param repositoryUrl string = '' // e.g. https://github.com/<you>/aiff-transparency-tracker
param branch string = 'main'

resource staticSite 'Microsoft.Web/staticSites@2023-12-01' = {
  name: name
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    repositoryUrl: repositoryUrl
    branch: branch
    buildProperties: {
      appLocation: 'site'
      apiLocation: ''
      outputLocation: ''
      skipGithubActionWorkflowGeneration: true // we ship our own workflow in .github/workflows/deploy.yml
    }
  }
}

output defaultHostname string = staticSite.properties.defaultHostname
output resourceId string = staticSite.id
