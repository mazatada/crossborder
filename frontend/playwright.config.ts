import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5001";

export default defineConfig({
	testDir: "./playwright/tests",
	use: {
		baseURL,
		trace: "on-first-retry",
	},
	projects: [
		{
			name: "api",
		},
	],
});
