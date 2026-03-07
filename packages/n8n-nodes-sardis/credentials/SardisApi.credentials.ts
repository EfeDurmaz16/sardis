import {
  ICredentialType,
  INodeProperties,
} from 'n8n-workflow';

export class SardisApi implements ICredentialType {
  name = 'sardisApi';
  displayName = 'Sardis API';
  documentationUrl = 'https://sardis.sh/docs';
  properties: INodeProperties[] = [
    {
      displayName: 'API Key',
      name: 'apiKey',
      type: 'string',
      typeOptions: { password: true },
      default: '',
      required: true,
      description: 'Your Sardis API key (starts with sk_)',
    },
    {
      displayName: 'Base URL',
      name: 'baseUrl',
      type: 'string',
      default: 'https://api.sardis.sh',
      description: 'Sardis API base URL',
    },
  ];
}
