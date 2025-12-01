import axios, { AxiosInstance } from "axios";

export interface MandateExecutionResponse {
  mandate_id: string;
  status: string;
  tx_hash: string;
  chain: string;
  audit_anchor: string;
}

export interface ExecutePaymentInput {
  mandate: Record<string, unknown>;
}

export class SardisClient {
  private http: AxiosInstance;

  constructor(baseUrl: string, apiKey: string) {
    this.http = axios.create({
      baseURL: baseUrl.replace(/\/$/, ""),
      headers: { "x-api-key": apiKey },
    });
  }

  async executePayment(input: ExecutePaymentInput): Promise<MandateExecutionResponse> {
    const { data } = await this.http.post<MandateExecutionResponse>("/api/v2/mandates/execute", input);
    return data;
  }
}
