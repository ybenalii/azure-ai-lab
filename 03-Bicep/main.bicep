param location string = resourceGroup().location
param name string
param principalId string
param modelName string
param modelVersion string

resource ai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: name
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource chat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: ai
  name: 'chat'
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
  }
}

var openAiUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource ra 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ai.id, principalId, openAiUser)
  scope: ai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUser)
    principalId: principalId
    principalType: 'User'
  }
}

output endpoint string = ai.properties.endpoints['OpenAI Language Model Instance API']
