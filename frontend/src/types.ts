export type HSRuleHit = {
	code: string;
	confidence: number;
	rationale: string[];
	required_uom: string;
};
export type HSResponse = {
	hs_candidates: HSRuleHit[];
	duty_rate: { ad_valorem_pct: number; additional: string[] };
	risk_flags: { ad_cvd: boolean; import_alert: boolean };
	quota_applicability: string;
	review_required: boolean;
};

export type HSRequest = {
	product: {
		name: string;
		category: string;
		process: string[];
		ingredients: { id: string }[];
	};
};

export type PackPayload = {
	traceId: string;
	hs_code: string;
	required_uom: string;
	invoice_uom: string;
	invoice_payload?: {
		number: string;
		qty: number;
		uom: string;
	};
};

export type PNProduct = {
	name: string;
	description: string;
	hs_code: string;
	origin_country: string;
};

export type PNLogistics = {
	mode: "AIR" | "EXPRESS" | "SEA";
	carrier?: string;
	port_of_entry: string;
	arrival_date: string;
	quantity?: number;
	pkg_type?: string;
};

export type PartyInfo = { name: string };

export type PNPayload = {
	traceId: string;
	product: PNProduct;
	logistics: PNLogistics;
	importer: PartyInfo;
	consignee: PartyInfo;
	label_media_id: string;
};

export type Job = {
	type: "pack" | "pn";
	status:
		| "queued"
		| "running"
		| "submitted"
		| "completed"
		| "accepted"
		| "rejected"
		| "error";
	trace_id: string;
	artifacts?: {
		media_id: string;
		sha256: string;
		size: number;
		type: string;
	}[];
	error?: unknown;
};
