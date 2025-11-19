import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./playwright/tests",
	use: {
		baseURL: "http://127.0.0.1:5001",
		trace: "on-first-retry",
	},
	projects: [
		{
			name: "api",
		},
	],
});
