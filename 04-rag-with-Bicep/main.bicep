param location string = resourceGroup().location
param name string                 // name of the AI Services account
param principalId string          // your Entra ID object id (the "who" that receives the roles)
param modelName string            // chat model, e.g. gpt-5.4-pro
param modelVersion string         // chat model version
param searchName string           // name of the Azure AI Search service
param searchLocation string = 'francecentral'   // Search lives in its own region (swedencentral was full)

// =====================================================================
// SERVICES (things that actually exist in Azure)
// =====================================================================

// SERVICE: the AI Services account. Empty "box" that will host the models.
resource ai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: name        // required for Entra ID (keyless) auth
    disableLocalAuth: true           // API keys disabled: only identity + roles work
    publicNetworkAccess: 'Enabled'   // will be locked down in project 06
  }
}

// SERVICE (child of "ai"): the chat model. Writes the final answers.
// Your Python code calls it with model="chat" (the deployment name, not the real model name).
resource chat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: ai                         // installed INSIDE the AI Services account
  name: 'chat'
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
  }
}

// SERVICE (child of "ai"): the embedding model. Turns text into numbers (its "meaning").
// Your Python code calls it with model="embed".
resource embed 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: ai
  name: 'embed'
  dependsOn: [ chat ]                // deploy one model at a time (Azure often rejects parallel ones)
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: 'text-embedding-3-small', version: '1' }
  }
}

// SERVICE: Azure AI Search. Separate service = the "librarian".
// Stores the document chunks (and their vectors) and finds the best ones for a question.
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: searchLocation
  sku: { name: 'basic' }             // billed hourly, even when idle: clean up when done
  properties: {
    authOptions: {
      aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' }   // accept Entra ID login
    }
  }
}

// =====================================================================
// ROLES / "BADGES" (they create nothing: they only GRANT permissions)
// Every role assignment answers 3 questions:
//   scope            -> ON what?   (which service)
//   roleDefinitionId -> WHICH right? (the role's fixed id)
//   principalId      -> FOR whom?  (you)
// =====================================================================

// Fixed ids of built-in roles (identical for everyone in Azure)
var openAiUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'                  // Cognitive Services OpenAI User
var searchServiceContributor = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'     // Search Service Contributor (verify!)
var searchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'   // Search Index Data Contributor (verify!)

// ROLE ASSIGNMENT: "ra" = Role Assignment (just a nickname for this block).
// Gives YOU the right to call the models. Placed on "ai", so it covers BOTH chat and embed.
// Without it you get 401/403, because keys are disabled and you would have no permission.
resource ra 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai.id, principalId, openAiUser)   // required unique name; same inputs = same name = no duplicates (idempotent)
  scope: ai                                    // ON: the AI Services account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUser)   // WHICH: OpenAI User
    principalId: principalId                   // FOR: you
    principalType: 'User'                      // a person (not an app or a group)
  }
}

// ROLE ASSIGNMENT on Search (control plane): lets you CREATE/MANAGE the index (build the shelf).
resource raSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalId, searchServiceContributor)
  scope: search                                // ON: the Search service
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributor)
    principalId: principalId
    principalType: 'User'
  }
}

// ROLE ASSIGNMENT on Search (data plane): lets you WRITE/READ documents in the index (store and look up the books).
// Separate from the one above: having one does NOT give you the other.
resource raSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalId, searchIndexDataContributor)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributor)
    principalId: principalId
    principalType: 'User'
  }
}

// =====================================================================
// OUTPUTS (values returned after deployment, to copy into your .env)
// =====================================================================
output endpoint string = 'https://${name}.cognitiveservices.azure.com/'     // -> AZURE_OPENAI_ENDPOINT
output searchEndpoint string = 'https://${searchName}.search.windows.net'   // -> SEARCH_ENDPOINT
