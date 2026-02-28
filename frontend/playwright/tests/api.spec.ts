import { test, expect } from "@playwright/test";

test.describe("backend API smoke", () => {
	test("health endpoint responds quickly", async ({ request }) => {
		const response = await request.get("/v1/health");
		expect(response.status()).toBe(200);
		const body = await response.json();
		expect(body.status).toBe("ok");
		expect(body.ts).toBeTruthy();
	});

	test("translate returns mock terms", async ({ request }) => {
		const response = await request.post("/v1/translate/ingredients", {
			data: { text_ja: "小麦粉" },
		});
		expect(response.status()).toBe(200);
		const body = await response.json();
		expect(Array.isArray(body.terms)).toBeTruthy();
	});

	test("classify requires ingredients", async ({ request }) => {
		const response = await request.post("/v1/classify/hs", {
			data: { product: { name: "Sample Snack", ingredients: [] } },
		});
		expect(response.status()).toBe(422);
		const body = await response.json();
		expect(body.violations?.[0]?.field).toBe("product.ingredients");
	});

	test("classify returns candidates", async ({ request }) => {
		const response = await request.post("/v1/classify/hs", {
			data: {
				product: {
					name: "Sample Snack",
					ingredients: [{ id: "ing_wheat_flour", pct: 60 }],
					process: ["baking"],
				},
			},
		});
		expect(response.status()).toBe(200);
		const body = await response.json();
		expect(body.hs_candidates?.[0]?.code).toBe("1905.90");
	});

	test("translate→classify→docs→PN queues successfully", async ({ request }) => {
		const traceId = `pw-trace-${Date.now()}`;

		const translateResp = await request.post("/v1/translate/ingredients", {
			data: { text_ja: "砂糖" },
		});
		expect(translateResp.status()).toBe(200);

		const classifyResp = await request.post("/v1/classify/hs", {
			data: {
				product: {
					name: "Sample Snack",
					ingredients: [{ id: "ing_wheat_flour", pct: 60 }],
					process: ["baking"],
				},
			},
		});
		expect(classifyResp.status()).toBe(200);
		const classifyBody = await classifyResp.json();
		const hs_code = classifyBody.hs_candidates?.[0]?.code ?? "1905.90";

		const docsResp = await request.post("/v1/docs/clearance-pack", {
			data: {
				traceId,
				hs_code,
				required_uom: "kg",
				invoice_uom: "kg",
				invoice_payload: { lines: [{ sku: "SKU1", qty: 1 }] },
			},
		});
		const docsRespBody = await docsResp.text();
		expect(docsResp.status(), `docs/clearance-pack responded with: ${docsRespBody}`).toBe(202);
		const docsBody = JSON.parse(docsRespBody);
		expect(docsBody.status).toBe("queued");

		const pnResp = await request.post("/v1/fda/prior-notice", {
			data: {
				traceId,
				product: { name: "Sample", category: "Food" },
				logistics: { arrival: "2025-12-01T00:00:00Z" },
				importer: { name: "Importer Inc." },
				consignee: { name: "Consignee LLC" },
			},
		});
		expect(pnResp.status()).toBe(202);
		const pnBody = await pnResp.json();
		expect(pnBody.status).toBe("queued");
	});
});
