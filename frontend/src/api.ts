import axios from "axios";
import type {
	HSRequest,
	HSResponse,
	Job,
	PackPayload,
	PNPayload,
} from "./types";

export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE });

export async function classifyHS(payload: HSRequest): Promise<HSResponse> {
	const { data } = await api.post<HSResponse>("/v1/classify/hs", payload);
	return data;
}

export async function createPack(payload: PackPayload): Promise<string> {
	const { data } = await api.post<{ job_id: string }>(
		"/v1/docs/clearance-pack",
		payload,
	);
	return data.job_id;
}

export async function createPN(payload: PNPayload): Promise<string> {
	const { data } = await api.post<{ job_id: string }>(
		"/v1/fda/prior-notice",
		payload,
	);
	return data.job_id;
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get<Job>(`/v1/jobs/${id}`);
  return data;
}

export function mediaUrl(mediaId: string) {
  return `${import.meta.env.VITE_API_BASE}/v1/media/${encodeURIComponent(mediaId)}`;
}
