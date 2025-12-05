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

export interface ExecuteAp2PaymentInput {
  intent: Record<string, unknown>;
  cart: Record<string, unknown>;
  payment: Record<string, unknown>;
}

export interface ExecuteAp2PaymentResponse {
  mandate_id: string;
  ledger_tx_id: string;
  chain_tx_hash: string;
  chain: string;
  audit_anchor: string;
  status: string;
  compliance_provider?: string;
  compliance_rule?: string;
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

  async executeAp2Payment(input: ExecuteAp2PaymentInput): Promise<ExecuteAp2PaymentResponse> {
    const { data } = await this.http.post<ExecuteAp2PaymentResponse>("/api/v2/ap2/payments/execute", input);
    return data;
  }
}
