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
			data: { product: { ingredients: [] } },
		});
		expect(response.status()).toBe(422);
		const body = await response.json();
		expect(body.error.code).toBe("UNPROCESSABLE");
	});

	test("classify returns candidates", async ({ request }) => {
		const response = await request.post("/v1/classify/hs", {
			data: { product: { ingredients: ["小麦粉"] } },
		});
		expect(response.status()).toBe(200);
		const body = await response.json();
		expect(body.hs_candidates?.[0]?.code).toBe("1905.90");
	});
});
